from dotenv import load_dotenv
import html
import http.server
import json
import logging
import math
import os
import psycopg
import re
from urllib.parse import urlparse, parse_qs
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


PAGE_SIZE = 10

def get_images_metadata(page: int):
    count_query = "SELECT COUNT(*) FROM images;"
    query = """
        SELECT id, filename, original_name, size, upload_time, file_type
        FROM images
        ORDER BY upload_time DESC
        LIMIT %s OFFSET %s;
        """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(count_query)
            total_rows = cursor.fetchone()[0]

            total_pages = max(1, math.ceil(total_rows / PAGE_SIZE))
            page = min(max(page, 1), total_pages)

            cursor.execute(query, (PAGE_SIZE, (page - 1) * PAGE_SIZE))
            return cursor.fetchall(), page, total_pages


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


def delete_image_metadata(image_id:int):
    query = """
        DELETE FROM images
        WHERE id = %s
        RETURNING filename;
        """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (image_id,))
            row = cursor.fetchone()
            return row[0] if row else None


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        paths = {
            '/': 'index.html',
            '/upload': 'upload.html',
        }

        if self.path in paths:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            with open(f"templates/{paths[self.path]}", 'r') as file:
                self.wfile.write(file.read().encode())

        elif urlparse(self.path).path == '/images-list':
            self.send_images_list()

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

        elif self.path.startswith('/delete/'):
            self.handle_delete()

        else:
            self.send_response(404)
            self.end_headers()
            logger.error(f"Error: unsupported path {self.path} for POST request.")


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


    def send_images_list(self):
        query = parse_qs(urlparse(self.path).query)
        try:
            page = int(query.get('page', ['1'])[0])
        except ValueError:
            page = 1

        try:
            images, page, total_pages = get_images_metadata(page)
        except psycopg.Error as e:
            self.send_response(500)
            self.end_headers()
            logger.error(f"Error: database error while listing images: {e}")
            return

        if images:
            rows = ""
            for image_id, filename, original_name, size, upload_time, file_type in images:
                rows += f"""
                    <tr>
                        <td><a href="http://localhost:8080/images/{html.escape(filename)}" target="_blank">{html.escape(filename)}</a></td>
                        <td>{html.escape(original_name)}</td>
                        <td>{size / 1024:.1f}</td>
                        <td>{upload_time:%Y-%m-%d %H:%M:%S}</td>
                        <td>{html.escape(file_type)}</td>
                        <td>
                            <form method="post" action="/delete/{image_id}" class="delete-form">
                                <button type="submit" class="delete-btn" title="Delete" aria-label="Delete">
                                    <img class="delete-img" src="/static/img/icon/delete.png" alt="">
                                </button>
                            </form>
                        </td>
                    </tr>"""
            content = f"""
                <table class="images-table">
                    <thead>
                        <tr>
                            <th>Filename</th><th>Original name</th>
                            <th>Size (KB)</th><th>Upload time</th>
                            <th>File type</th><th>Delete</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>"""
            prev_btn = (
                f'<a class="pagination__btn" href="/images-list?page={page - 1}">Previous page</a>'
                if page > 1 else
                '<span class="pagination__btn pagination__btn--disabled">Previous page</span>'
            )
            next_btn = (
                f'<a class="pagination__btn" href="/images-list?page={page + 1}">Next page</a>'
                if page < total_pages else
                '<span class="pagination__btn pagination__btn--disabled">Next page</span>'
            )
            content += f"""
                <nav class="pagination">
                    {prev_btn}
                    <span>Page {page}/{total_pages}</span>
                    {next_btn}
                </nav>"""
        else:
            content = '<p class="upload__promt">No images uploaded yet.</p>'

        with open("templates/images-list.html", "r") as file:
            page = file.read().replace("{{content}}", content)

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(page.encode())


    def handle_delete(self):
        try:
            image_id = int(self.path.split('/')[-1])
        except ValueError:
            self.send_response(400)
            self.end_headers()
            logger.error(f"Error: invalid image id in {self.path}.")
            return

        try:
            filename = delete_image_metadata(image_id)
        except psycopg.Error as e:
            self.send_response(500)
            self.end_headers()
            logger.error(f"Error: database error while deleting image id {image_id}: {e}")
            return

        if filename is None:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write("Image not found".encode())
            logger.error(f"Error: image id {image_id} not found in database.")
            return

        try:
            os.remove(f"images/{filename}")
            logger.info(f"Success: image {filename} deleted (id {image_id}).")
        except OSError as e:
            logger.error(f"Error: record {image_id} deleted, but file {filename} was not removed: {e}")

        self.send_response(303)
        self.send_header('Location', '/images-list')
        self.end_headers()


server = http.server.ThreadingHTTPServer(('0.0.0.0', 8000), Handler)
if __name__ == '__main__':
    server.serve_forever()
