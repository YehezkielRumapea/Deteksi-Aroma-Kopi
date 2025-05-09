from sqlalchemy.orm import Session
from app.schemas import SensorCreate
from app.models import SensorData, ApiLogs
from fastapi import HTTPException
from datetime import datetime

def create_sensor_data(db: Session, sensor_data: SensorCreate):
    try:
        if not sensor_data:
            raise HTTPException(status_code=500, detail="Failed to read sensor data")

        db_sensor = SensorData(
            timestamp=datetime.now(),
            mq135=sensor_data.mq135,
            mq2=sensor_data.mq2,
            mq4=sensor_data.mq4,
            mq7=sensor_data.mq7,
            kualitas=sensor_data.kualitas
        )

        db.add(db_sensor)
        db.commit()
        db.refresh(db_sensor)
        return db_sensor

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def get_sensor_data(db: Session, sensor_id: int):
    sensor_data = db.query(SensorData).filter(SensorData.id == sensor_id).first()
    if not sensor_data:
        raise HTTPException(status_code=404, detail="Sensor data not found")
    return sensor_data

def get_all_sensor_data(db: Session, skip: int = 0, limit: int = 10):
    sensor_data = db.query(SensorData).offset(skip).limit(limit).all()
    if not sensor_data:
        raise HTTPException(status_code=404, detail="No sensor data found")
    return sensor_data

def delete_all_sensor_data(db: Session):
    deleted_rows = db.query(SensorData).delete()
    db.commit()

    if deleted_rows == 0:
        raise HTTPException(status_code=404, detail="No sensor data to delete")

    return {"message": f"Deleted {deleted_rows} sensor data entries successfully"}

def get_logs_api(db: Session, limit: int = 10):
    return db.query(ApiLogs).order_by(ApiLogs.timestamp.desc()).limit(limit).all()

def create_log(db: Session, message: str):
    log = ApiLogs(message=message, timestamp=datetime.now())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def tentukan_kualitas(data: dict) -> str:
    # Default jika tidak ada data sensor
    if not any(data.get(sensor) for sensor in ["mq135", "mq2", "mq4", "mq7"]):
        return "Tidak Diketahui"

    # Ambil nilai sensor yang tersedia
    mq135 = float(data["mq135"]) if data.get("mq135") else None
    mq2 = float(data["mq2"]) if data.get("mq2") else None
    mq4 = float(data["mq4"]) if data.get("mq4") else None
    mq7 = float(data["mq7"]) if data.get("mq7") else None

    # Kriteria kualitas berdasarkan rentang 0-5
    baik = True
    sedang = True

    if mq135 is not None:
        if mq135 >= 4.0:
            baik = False
            sedang = False
        elif mq135 >= 2.0:
            baik = False
    if mq2 is not None:
        if mq2 >= 3.5:
            baik = False
            sedang = False
        elif mq2 >= 1.5:
            baik = False
    if mq4 is not None:
        if mq4 >= 4.0:
            baik = False
            sedang = False
        elif mq4 >= 2.0:
            baik = False
    if mq7 is not None:
        if mq7 >= 3.0:
            baik = False
            sedang = False
        elif mq7 >= 1.0:
            baik = False

    if baik:
        return "Baik"
    elif sedang:
        return "Sedang"
    return "Buruk"