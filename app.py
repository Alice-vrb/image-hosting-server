import http.server
import json
import os
import re
import uuid


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


    def do_POST(self):
        if self.path == '/upload':
            data, upload_name = self.extract_file_data()
            filename = f"{uuid.uuid4().hex}.{upload_name.split('.')[-1]}"

            os.makedirs(os.path.dirname(f"images/{filename}"), exist_ok=True)

            with open(f"images/{filename}", 'wb') as file:
                file.write(data)

            response = json.dumps({
                'name': filename,
                'url': f'http://localhost:8000/images/{filename}'
            }).encode()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write(response)
        else:
            self.send_response(404)
            self.end_headers()


    def get_static_info(self): # -> content-type, file path
        if self.path.endswith(".css"):
            content_type = "text/css"
        elif self.path.endswith(".js"):
            content_type = "text/javascript"
        else:
            content_type = f"image/{self.path.split('.')[-1]}"

        file_path = f"static/{self.path.split('static/')[-1]}"

        return content_type, file_path

    def extract_file_data(self):
        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        boundary = self.headers["Content-Type"].split("boundary=")[-1].encode()
        start = body.find(b"\r\n\r\n") + 4
        end = body.find(b"\r\n--" + boundary, start)
        data = body[start:end]

        upload_name = re.search(
            rb'filename="([^"]+)"',
            body
        ).group(1).decode()

        return data, upload_name


server = http.server.HTTPServer(('localhost', 8000), Handler)
if __name__ == '__main__':
    server.serve_forever()
