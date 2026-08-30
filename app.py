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
        else:
            self.send_response(404)
            self.end_headers()


server = http.server.HTTPServer(('localhost', 8000), Handler)
if __name__ == '__main__':
    server.serve_forever()
