import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import SensorData, ApiLogs

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi koneksi database
DB_USER = "postgres"  # Perbaiki typo dari 'postgress'
DB_PASSWORD = "postgress"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "e_nose_db"

# Membuat URL koneksi database
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Membuat engine
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"❌ Gagal membuat engine database: {e}")
    raise

def init_db():
    try:
        # Buat semua tabel yang didefinisikan di models
        Base.metadata.drop_all(bind=engine)  # Hapus tabel lama
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tabel database berhasil dibuat: sensor_data, api_logs")
    except Exception as e:
        logger.error(f"❌ Gagal membuat tabel database: {e}")
        raise

if __name__ == "__main__":
    init_db()