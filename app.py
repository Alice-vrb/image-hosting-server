import http.server

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


    def get_static_info(self): # -> content-type, file path
        if self.path.endswith(".css"):
            content_type = "text/css"
        elif self.path.endswith(".js"):
            content_type = "text/javascript"
        else:
            content_type = f"image/{self.path.split('.')[-1]}"

        file_path = f"static/{self.path.split('static/')[-1]}"

        return content_type, file_path


server = http.server.HTTPServer(('localhost', 8000), Handler)
if __name__ == '__main__':
    server.serve_forever()
