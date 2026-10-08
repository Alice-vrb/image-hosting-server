from dotenv import load_dotenv
import http.server
import json
import logging
import os
import psycopg
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


load_dotenv()

def get_connection():
    return psycopg.connect(
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        port=os.getenv("DB_PORT"),
        host=os.getenv("DB_HOST"),
        connect_timeout=5
    )


def insert_image_metadata(filename: str, original_name: str, size: int, file_type: str):
    query = """
        INSERT INTO images (filename, original_name, size, file_type)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (filename, original_name, size, file_type))
            return cursor.fetchone()[0]


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

            for data, original_name in files:
                is_valid, error_message = self.validate_file(data, original_name)
                if not is_valid:
                    errors.append({'file': original_name, 'error': error_message})
                    logger.error(f"Error: {error_message} ({original_name}).")
                    continue

                filename = f"{uuid.uuid4().hex}.{original_name.split('.')[-1]}"
                os.makedirs('images', exist_ok=True)

                with open(f"images/{filename}", 'wb') as file:
                    file.write(data)

                file_type = original_name.split('.')[-1].lower()

                try:
                    image_id = insert_image_metadata(filename, original_name, len(data), file_type)
                except psycopg.Error as e:
                    os.remove(f"images/{filename}")
                    errors.append({'file': original_name, 'error': 'Database error'})
                    logger.error(f"Error: database error: {e} ({original_name}).")
                    continue

                results.append({
                    'filename': filename,
                    'url': f'http://localhost:8080/images/{filename}'
                })

                logger.info(f"Success: image {filename} uploaded. Inserted into db with id {image_id}")

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
            original_name = filename_match.group(1).decode()

            start = part.find(b"\r\n\r\n") + 4
            end = part.rfind(b"\r\n")
            data = part[start:end]

            files.append((data, original_name))

        return files


    ALLOWED_EXTENSIONS = ('jpg', 'jpeg', 'png', 'gif')
    MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

    def validate_file(self, data, original_name):
        extension = original_name.split('.')[-1].lower() if '.' in original_name else ''

        if extension not in self.ALLOWED_EXTENSIONS:
            return False, f"Invalid file extension: .{extension}"

        if len(data) > self.MAX_SIZE_BYTES:
            return False, f"File exceeds maximum size of {self.MAX_SIZE_BYTES // (1024 * 1024)}MB"

        return True, None


server = http.server.ThreadingHTTPServer(('0.0.0.0', 8000), Handler)
if __name__ == '__main__':
    server.serve_forever()
