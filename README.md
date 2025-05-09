#!/bin/bash

# Nama Proyek
PROJECT_NAME="e-nose-backend"

## **Deskripsi Proyek**
E-Nose Backend adalah backend untuk proyek e-nose berbasis IoT dan Edge Impulse. Backend ini menangani:  
✅ Pengambilan data dari sensor  
✅ Penyimpanan ke database PostgreSQL  
✅ Penyediaan API untuk komunikasi dengan frontend dan AI  

## **Struktur Direktori**
\`\`\`
e-nose-backend/        # Direktori utama backend
│── README.md          # Dokumentasi proyek
│── requirements.txt   # Daftar library yang digunakan
│── app/               # Folder utama aplikasi
│   ├── __init__.py    # File init untuk modularisasi
│   ├── main.py        # Entry point FastAPI
│   ├── database.py    # Koneksi database PostgreSQL
│   ├── models.py      # Model database SQLAlchemy
│   ├── config.py      # Konfigurasi aplikasi (misalnya variabel lingkungan)
│   ├── routes/        # Folder untuk API endpoints
│   │   ├── __init__.py
│   │   ├── sensor.py  # Endpoint untuk data sensor
│   ├── schemas/       # Folder untuk skema data (Pydantic)
│   │   ├── __init__.py
│   │   ├── sensor.py  # Skema data sensor
│   ├── services/      # Folder untuk logika bisnis
│   │   ├── __init__.py
│   │   ├── sensor_service.py  # Layanan pemrosesan data sensor
│   │   ├── sensor_reader.py  # Membaca data sensor
\`\`\`


## **Library yang Digunakan**
| Library           | Fungsi |
|------------------|-------------------------------------------------|
| \`fastapi\`        | Framework untuk membangun API backend |
| \`uvicorn\`        | Server ASGI untuk menjalankan FastAPI |
| \`SQLAlchemy\`     | ORM untuk mengelola database PostgreSQL |
| \`psycopg2\`       | Driver PostgreSQL untuk Python |
| \`pydantic\`       | Validasi data dan skema dengan tipe data Python |
| \`python-dotenv\`  | Membaca konfigurasi dari file \`.env\` |

## **Konfigurasi Database**
Pastikan untuk menyertakan file **.env** dengan isi berikut:  
\`\`\`env
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
DB_NAME=e_nose_db
\`\`\`

## **Menjalankan Server**
Gunakan perintah berikut untuk menjalankan server FastAPI:  
\`\`\`bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
\`\`\`
API akan berjalan di \`http://localhost:8000\`.

