# Image Hosting Server

A simple Python-based HTTP server for uploading, storing and viewing images.

![Image Hosting Server main image](assets/img_1.png)

---

## Built With
* **Backend:** Pure Python
* **Web Server:** Nginx
* **Frontend:** HTML5, CSS3, JavaScript
* **Containerization:** Docker & Docker Compose

---

## Features
* Image upload (.jpg, .png, .gif, up to 5MB)
* File format and size validation
* Unique name and url generation for each image
* File serving through Nginx

---

## Project Structure
```
image-hosting-server/
├── assets/             # README image assets
├── images/             # Uploaded images
├── logs/
│   └── app.log         # Application logs
├── static/             # CSS, JS & image assets
├── templates/          # HTML
├── .dockerignore
├── .gitignore
├── app.py              # HTTP server
├── docker-compose.yaml
├── Dockerfile
├── nginx.conf          # Nginx configuration
└── nginx.Dockerfile
```

![Main site page](assets/img_2.png)

---

## Requirements
* Python 3.12+
* Docker & Docker Compose

---

## Launching
```
git clone git@github.com:Alice-vrb/image-hosting-server.git
cd image-hosting-server
docker compose up --build
```

Open http://localhost:8080

---

## Application Pages
* **/** - Home page
* **/upload** - Image upload page
* **/images** - Image list
* **/images/{filename}** - Specific image viewing page

![Image upload page & Image list](assets/img_3.png)
