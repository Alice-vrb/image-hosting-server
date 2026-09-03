FROM python:3.12-alpine
WORKDIR /app
COPY . .
CMD ["python3", "app.py"]