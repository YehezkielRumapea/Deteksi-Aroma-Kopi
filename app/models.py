
from sqlalchemy import Column, Integer, Float, DateTime, String
from sqlalchemy.sql import func  # Untuk server default timestamp
from app.database import Base  # Impor Base dari database.py
import datetime

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    mq135 = Column(Float, nullable=True)
    mq2 = Column(Float, nullable=True)
    mq4 = Column(Float, nullable=True)
    mq7 = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=func.now(), server_default=func.now())
    kualitas = Column(String, nullable=True)  # Label kualitas kopi


class ApiLogs(Base):
    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, index=True)
    method = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status_code = Column(Integer)
    response = Column(String)