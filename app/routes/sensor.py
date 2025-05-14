from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.sensor_service import create_sensor_data, get_all_sensor_data, get_db_data_for_interval
from app.models import SensorData
from app.config import sensor_status  # Diubah dari app.main
import asyncio
from fastapi.responses import StreamingResponse
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensor", tags=["sensor"])

active_connections = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    active_connections.append(websocket)
    last_sent_id = None

    try:
        while True:
            if not any(sensor_status[s].is_set() for s in sensor_status):
                await websocket.send_json({"message": "Sensor stopped"})
                break
            latest_data = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
            if latest_data and latest_data.id != last_sent_id:
                last_sent_id = latest_data.id
                data = {
                    "id": latest_data.id,
                    "mq135": latest_data.mq135,
                    "mq2": latest_data.mq2,
                    "mq4": latest_data.mq4,
                    "mq7": latest_data.mq7,
                    "timestamp": latest_data.timestamp.isoformat(),
                    "kualitas": latest_data.kualitas
                }
                active_sensors = []
                if latest_data.mq135 is not None:
                    active_sensors.append("mq135")
                if latest_data.mq2 is not None:
                    active_sensors.append("mq2")
                if latest_data.mq4 is not None:
                    active_sensors.append("mq4")
                if latest_data.mq7 is not None:
                    active_sensors.append("mq7")
                sensor_name = "all" if len(active_sensors) >= 4 else active_sensors[0] if active_sensors else "unknown"
                data["sensor"] = sensor_name
                data["log"] = f"Data aroma kopi {sensor_name.upper()} tersimpan: {', '.join([f'{k.upper()}={data[k]:.4f}' for k in active_sensors if data[k] is not None])}, Kualitas={data['kualitas']}"
                await websocket.send_json(data)
                logger.info(f"WebSocket sent: {data['log']}")
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket disconnected")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

@router.get("/stream")
async def stream_sensor_data(db: Session = Depends(get_db)):
    async def event_generator():
        last_id = None
        while True:
            if not any(sensor_status[s].is_set() for s in sensor_status):
                yield "data: {\"message\": \"Sensor stopped\"}\n\n"
                break
            latest = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
            if latest and latest.id != last_id:
                last_id = latest.id
                data = {
                    "waktu": latest.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "mq135": latest.mq135,
                    "mq2": latest.mq2,
                    "mq4": latest.mq4,
                    "mq7": latest.mq7,
                    "kualitas": latest.kualitas
                }
                yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.delete("/delete")
def delete_sensor_data(db: Session = Depends(get_db)):
    try:
        result = get_all_sensor_data(db)
        deleted_rows = db.query(SensorData).delete()
        db.commit()
        logger.info(f"Deleted {deleted_rows} sensor data entries")
        return {"message": f"Deleted {deleted_rows} sensor data entries successfully"}
    except Exception as e:
        logger.error(f"Failed to delete data: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal menghapus data: {e}")

@router.get("/data/db/{interval}")
async def get_sensor_data_db(interval: str, db: Session = Depends(get_db)):
    valid_intervals = ["3s", "30s", "1m", "5m", "10m"]
    if interval not in valid_intervals:
        raise HTTPException(status_code=400, detail="Interval tidak valid")
    
    data = get_db_data_for_interval(db, interval)
    logger.info(f"Fetched {len(data)} data points from DB for interval {interval}")
    return data