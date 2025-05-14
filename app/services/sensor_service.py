from sqlalchemy.orm import Session
from app.schemas.sensor import SensorCreate
from app.models import SensorData, ApiLogs
from fastapi import HTTPException
from datetime import datetime, timedelta
from sqlalchemy.sql import func
import csv
import os
import logging

logger = logging.getLogger(__name__)

def create_sensor_data(db: Session, sensor_data: SensorCreate):
    try:
        if not sensor_data:
            raise HTTPException(status_code=500, detail="Failed to read sensor data")

        db_sensor = SensorData(
            timestamp=sensor_data.timestamp,
            mq135=sensor_data.mq135,
            mq2=sensor_data.mq2,
            mq4=sensor_data.mq4,
            mq7=sensor_data.mq7,
            kualitas=sensor_data.kualitas,
            exported=False
        )

        db.add(db_sensor)
        db.commit()
        db.refresh(db_sensor)

        log_message = f"Data aroma kopi disimpan: {sensor_data.dict()}"
        db_log = ApiLogs(
            endpoint="/sensor/create",
            method="POST",
            status_code=200,
            response=log_message,
            timestamp=datetime.now()
        )
        db.add(db_log)
        db.commit()
        logger.info(log_message)

        return db_sensor

    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
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
    logs = db.query(ApiLogs).order_by(ApiLogs.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "endpoint": log.endpoint,
            "method": log.method,
            "status_code": log.status_code,
            "response": log.response,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]

def create_log(db: Session, endpoint: str, method: str, status_code: int, response: str):
    log = ApiLogs(
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response=response,
        timestamp=datetime.now()
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def tentukan_kualitas(data: dict) -> str:
    values = [float(data[key]) for key in ["mq135", "mq2", "mq4", "mq7"] if data.get(key) is not None]
    if not values:
        return "Tidak Terdeteksi"
    avg_value = sum(values) / len(values)
    if avg_value < 2.0:
        return "Kopi Ringan"
    elif avg_value < 3.5:
        return "Kopi Sedang"
    else:
        return "Kopi Kuat"

def export_sensor_data_to_csv(db: Session, output_dir: str):
    try:
        data = db.query(SensorData).filter(SensorData.exported == False).all()
        if not data:
            return {"message": "No new data to export"}

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        csv_file = os.path.join(output_dir, f"coffee_aroma_{timestamp}.csv")
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "timestamp", "mq135", "mq2", "mq4", "mq7", "kualitas"])
            writer.writeheader()
            for d in data:
                writer.writerow({
                    "id": d.id,
                    "timestamp": d.timestamp.isoformat(),
                    "mq135": d.mq135,
                    "mq2": d.mq2,
                    "mq4": d.mq4,
                    "mq7": d.mq7,
                    "kualitas": d.kualitas
                })

        db.query(SensorData).filter(SensorData.exported == False).update({"exported": True})
        db.commit()

        logger.info(f"Exported {len(data)} rows to {csv_file}")
        return {"message": f"Exported {len(data)} rows to {csv_file}"}

    except Exception as e:
        db.rollback()
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

def get_db_data_for_interval(db: Session, interval: str):
    try:
        time_threshold = datetime.utcnow() - timedelta(hours=1)
        interval_map = {
            "3s": "3 seconds",
            "30s": "30 seconds",
            "1m": "1 minute",
            "5m": "5 minutes",
            "10m": "10 minutes"
        }
        
        if interval not in interval_map:
            return []

        if interval == "3s":
            data = db.query(SensorData).filter(SensorData.timestamp >= time_threshold)\
                .order_by(SensorData.timestamp).all()
            return [
                {
                    "timestamp": d.timestamp.isoformat(),
                    "mq135": float(d.mq135) if d.mq135 is not None else None,
                    "mq2": float(d.mq2) if d.mq2 is not None else None,
                    "mq4": float(d.mq4) if d.mq4 is not None else None,
                    "mq7": float(d.mq7) if d.mq7 is not None else None,
                    "kualitas": d.kualitas
                }
                for d in data
            ]

        time_format = "%Y-%m-%d %H:%M:%S"
        if interval in ["30s", "1m"]:
            time_format = "%Y-%m-%d %H:%M:00"
        elif interval in ["5m", "10m"]:
            minute_divisor = 5 if interval == "5m" else 10
            data = db.query(
                func.strftime('%Y-%m-%d %H', SensorData.timestamp) +
                ':' +
                func.lpad((func.cast(func.strftime('%M', SensorData.timestamp), 'INTEGER') / minute_divisor) * minute_divisor, 2, '0') +
                ':00.000000'
                .label('time_bucket'),
                func.avg(SensorData.mq135).label('mq135'),
                func.avg(SensorData.mq2).label('mq2'),
                func.avg(SensorData.mq4).label('mq4'),
                func.avg(SensorData.mq7).label('mq7'),
                func.max(SensorData.kualitas).label('kualitas')
            ).filter(SensorData.timestamp >= time_threshold)\
             .group_by('time_bucket')\
             .order_by('time_bucket').all()
            
            return [
                {
                    "timestamp": d.time_bucket,
                    "mq135": float(d.mq135) if d.mq135 is not None else None,
                    "mq2": float(d.mq2) if d.mq2 is not None else None,
                    "mq4": float(d.mq4) if d.mq4 is not None else None,
                    "mq7": float(d.mq7) if d.mq7 is not None else None,
                    "kualitas": d.kualitas
                }
                for d in data
            ]

        seconds = 30 if interval == "30s" else 60
        data = db.query(
            func.strftime('%Y-%m-%d %H:%M:', SensorData.timestamp) +
            func.lpad((func.cast(func.strftime('%S', SensorData.timestamp), 'INTEGER') / seconds) * seconds, 2, '0') +
            '.000000'
            .label('time_bucket'),
            func.avg(SensorData.mq135).label('mq135'),
            func.avg(SensorData.mq2).label('mq2'),
            func.avg(SensorData.mq4).label('mq4'),
            func.avg(SensorData.mq7).label('mq7'),
            func.max(SensorData.kualitas).label('kualitas')
        ).filter(SensorData.timestamp >= time_threshold)\
         .group_by('time_bucket')\
         .order_by('time_bucket').all()

        return [
            {
                "timestamp": d.time_bucket,
                "mq135": float(d.mq135) if d.mq135 is not None else None,
                "mq2": float(d.mq2) if d.mq2 is not None else None,
                "mq4": float(d.mq4) if d.mq4 is not None else None,
                "mq7": float(d.mq7) if d.mq7 is not None else None,
                "kualitas": d.kualitas
            }
            for d in data
        ]

    except Exception as e:
        logger.error(f"Error fetching DB data for interval {interval}: {e}")
        return []