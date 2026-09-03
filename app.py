import http.server
import json
import logging
import os
import re
import uuid


os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        paths = {
            '/': 'index.html',
            '/upload': 'upload.html',
            '/images': 'images.html',
        }

        if self.path in paths:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            with open(f"templates/{paths[self.path]}", 'r') as file:
                self.wfile.write(file.read().encode())

        elif self.path.startswith('/static/'):
            content_type, file_path = self.get_static_info()

            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()

            with open(file_path, 'rb') as file:
                self.wfile.write(file.read())

        else:
            self.send_response(404)
            self.end_headers()
            logger.error(f"Error: path {self.path} not found.")

    def do_POST(self):
        if self.path == '/upload':
            files = self.extract_files_data()

            results = []
            errors = []

            for data, upload_name in files:
                is_valid, error_message = self.validate_file(data, upload_name)
                if not is_valid:
                    errors.append({'file': upload_name, 'error': error_message})
                    logger.error(f"Error: {error_message} ({upload_name}).")
                    continue

                filename = f"{uuid.uuid4().hex}.{upload_name.split('.')[-1]}"
                os.makedirs('images', exist_ok=True)

                with open(f"images/{filename}", 'wb') as file:
                    file.write(data)

                results.append({
                    'name': filename,
                    'url': f'http://localhost:8000/images/{filename}'
                })

                logger.info(f"Success: image {filename} uploaded.")

            if not results:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                logger.error(f"Error: no files passed validation ({len(errors)} rejected).")
                self.wfile.write(json.dumps({'errors': errors}).encode())
                return

            response = json.dumps({'files': results, 'errors': errors}).encode()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write(response)

        else:
            self.send_response(404)
            self.end_headers()
            logger.error(f"Error: unsupported path {self.path} for POST request.")


    def do_DELETE(self):
        if self.path == '/images':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body)
                filename = data.get('filename')
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                logger.error("Error: invalid JSON in DELETE request.")
                return

            if not filename:
                self.send_response(400)
                self.end_headers()
                logger.error("Error: DELETE request missing 'filename' field.")
                return

            file_path = f'images/{filename}'

            if os.path.isfile(file_path):
                os.remove(file_path)
                self.send_response(200)
                self.end_headers()
                logger.info(f"Success: image {filename} deleted.")
            else:
                self.send_response(404)
                self.end_headers()
                logger.error(f"Error: file {filename} not found for DELETE request.")
        else:
            self.send_response(404)
            self.end_headers()
            logger.error(f"Error: unsupported path {self.path} for DELETE request.")


    def get_static_info(self): # -> content-type, file path
        if self.path.endswith(".css"):
            content_type = "text/css"
        elif self.path.endswith(".js"):
            content_type = "text/javascript"
        else:
            content_type = f"image/{self.path.split('.')[-1]}"

        file_path = f"static/{self.path.split('static/')[-1]}"

        return content_type, file_path

    def extract_files_data(self):
        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        boundary = self.headers["Content-Type"].split("boundary=")[-1].encode()

        parts = body.split(b"--" + boundary)

        files = []
        for part in parts:
            if b'filename="' not in part:
                continue

            filename_match = re.search(rb'filename="([^"]+)"', part)
            if not filename_match:
                continue
            upload_name = filename_match.group(1).decode()

            start = part.find(b"\r\n\r\n") + 4
            end = part.rfind(b"\r\n")
            data = part[start:end]

            files.append((data, upload_name))

        return files


    ALLOWED_EXTENSIONS = ('jpg', 'jpeg', 'png', 'gif')
    MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

    def validate_file(self, data, filename):
        extension = filename.split('.')[-1].lower() if '.' in filename else ''

        if extension not in self.ALLOWED_EXTENSIONS:
            return False, f"Invalid file extension: .{extension}"

        if len(data) > self.MAX_SIZE_BYTES:
            return False, f"File exceeds maximum size of {self.MAX_SIZE_BYTES // (1024 * 1024)}MB"

        return True, None


server = http.server.ThreadingHTTPServer(('localhost', 8000), Handler)
if __name__ == '__main__':
    server.serve_forever()
