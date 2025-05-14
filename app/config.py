import os
from dotenv import load_dotenv

# Memuat variabel lingkungan dari file .env
load_dotenv()

# Konfigurasi database
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "e_nose_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

import threading

# Status untuk setiap sensor (threading.Event)
sensor_status = {
    "mq135": threading.Event(),
    "mq2": threading.Event(),
    "mq4": threading.Event(),
    "mq7": threading.Event(),
    "all": threading.Event()
}

# Thread untuk setiap sensor
sensor_threads = {
    "mq135": None,
    "mq2": None,
    "mq4": None,
    "mq7": None,
    "all": None
}
