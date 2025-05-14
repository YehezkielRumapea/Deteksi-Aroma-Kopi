from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)  # Ubah ke DateTime
    mq135 = Column(Float, nullable=True)
    mq2 = Column(Float, nullable=True)
    mq4 = Column(Float, nullable=True)
    mq7 = Column(Float, nullable=True)
    kualitas = Column(String)
    exported = Column(Boolean, default=False)

class ApiLogs(Base):
    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, index=True)
    method = Column(String)
    status_code = Column(Integer)
    response = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())