from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Konfigurasi koneksi database
DB_USER = "postgress"
DB_PASSWORD = "postgress"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "e_nose_db"  

# Membuat URL koneksi database
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Membuat engine untuk koneksi database
engine = create_engine(DATABASE_URL)

# Membuat sesi database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Membuat base model
Base = declarative_base()

# Dependency untuk mendapatkan  sesi database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
