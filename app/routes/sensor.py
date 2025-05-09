import time
import threading
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_db
from app.services import sensor_service
from app.services.sensor_reader import baca_sensor, start_sensor, stop_sensor, stop_all_sensors
from app.schemas.sensor import SensorCreate
from app.models import SensorData
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensor", tags=["sensor"])

active_connections = []

# Status dan thread untuk loop pembacaan
sensor_status = {
    "main_loop": threading.Event()
}
sensor_threads = {
    "main_loop": None
}

def sensor_loop():
    while True:
        if not sensor_status["main_loop"].is_set():
            break
        db = SessionLocal()
        try:
            sensor_data = baca_sensor()
            logger.info(f"Raw sensor data: {sensor_data}")
            
            # Tentukan kualitas
            kualitas = sensor_service.tentukan_kualitas(sensor_data)
            
            # Buat dictionary untuk SensorCreate
            sensor_model_data = {
                "timestamp": sensor_data.get("timestamp", time.strftime('%Y-%m-%d %H:%M:%S')),
                "mq135": float(sensor_data["mq135"]) if sensor_data.get("mq135") else None,
                "mq2": float(sensor_data["mq2"]) if sensor_data.get("mq2") else None,
                "mq4": float(sensor_data["mq4"]) if sensor_data.get("mq4") else None,
                "mq7": float(sensor_data["mq7"]) if sensor_data.get("mq7") else None,
                "kualitas": kualitas
            }
            logger.info(f"Sensor model data: {sensor_model_data}")
            
            sensor_model = SensorCreate(**sensor_model_data)
            sensor_service.create_sensor_data(db, sensor_model)
            logger.info(f"✅ Data tersimpan: {sensor_model_data}")
        except Exception as e:
            logger.error(f"❌ Gagal menyimpan data: {e}")
        finally:
            db.close()
        time.sleep(3)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    active_connections.append(websocket)
    last_sent_timestamp = None

    try:
        while True:
            latest_data = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
            if latest_data and latest_data.timestamp.isoformat() != last_sent_timestamp:
                last_sent_timestamp = latest_data.timestamp.isoformat()
                data = {
                    "id": latest_data.id,
                    "mq135": latest_data.mq135,
                    "mq2": latest_data.mq2,
                    "mq4": latest_data.mq4,
                    "mq7": latest_data.mq7,
                    "timestamp": latest_data.timestamp.isoformat(),
                    "kualitas": latest_data.kualitas
                }
                # Tentukan sensor yang aktif
                active_sensors = []
                if latest_data.mq135 is not None:
                    active_sensors.append("mq135")
                if latest_data.mq2 is not None:
                    active_sensors.append("mq2")
                if latest_data.mq4 is not None:
                    active_sensors.append("mq4")
                if latest_data.mq7 is not None:
                    active_sensors.append("mq7")
                sensor_name = "all" if len(active_sensors) >= 4 else "multiple" if active_sensors else "unknown"
                data["sensor"] = sensor_name
                data["log"] = f"Data {sensor_name.upper()} tersimpan: {', '.join([f'{k.upper()}={data[k]:.4f}' for k in active_sensors if data[k] is not None])}, Kualitas={data['kualitas'] or 'N/A'}"
                await websocket.send_json(data)
            await asyncio.sleep(3)  # Sinkronkan dengan interval sensor_loop
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@router.post("/start/{sensor_name}")
def start_sensor_endpoint(sensor_name: str, db: Session = Depends(get_db)):
    valid_sensors = ["mq135", "mq2", "mq4", "mq7", "all"]
    if sensor_name not in valid_sensors:
        return {"error": f"Sensor {sensor_name} tidak valid"}
    
    # Hentikan semua sensor jika "all" dipilih
    if sensor_name == "all":
        stop_all_sensors()
        sensor_status["main_loop"].clear()
        if sensor_threads["main_loop"]:
            sensor_threads["main_loop"].join(timeout=5.0)
            sensor_threads["main_loop"] = None
    
    # Aktifkan sensor
    start_sensor(sensor_name)
    
    # Mulai loop jika belum berjalan
    if not sensor_status["main_loop"].is_set():
        sensor_status["main_loop"].set()
        sensor_threads["main_loop"] = threading.Thread(target=sensor_loop, daemon=True)
        sensor_threads["main_loop"].start()
    
    logger.info(f"Sensor {sensor_name.upper()} diaktifkan")
    return {"message": f"Sensor {sensor_name.upper()} mulai mengambil data!"}

@router.post("/stop")
def stop_sensor(db: Session = Depends(get_db)):
    sensor_status["main_loop"].clear()
    if sensor_threads["main_loop"]:
        sensor_threads["main_loop"].join(timeout=5.0)
        sensor_threads["main_loop"] = None
    stop_all_sensors()
    logger.info("Semua sensor dihentikan")
    return {"message": "Semua sensor berhenti mengambil data!"}

@router.delete("/delete")
def delete_sensor_data(db: Session = Depends(get_db)):
    try:
        result = sensor_service.delete_all_sensor_data(db)
        logger.info("Semua data sensor dihapus")
        return result
    except Exception as e:
        logger.error(f"Gagal menghapus data: {e}")
        return {"error": f"Gagal menghapus data: {e}"}
        
# from fastapi import APIRouter, HTTPException
# from threading import Thread
# import threading
# import time
# from sensor_reader import baca_sensor
# from datetime import datetime

# router = APIRouter()

# # Flag untuk mengontrol sensor yang aktif
# sensor_flags = {
#     "mq135": False,
#     "mq2": False,
#     "mq4": False,
#     "mq7": False,
#     "all": False
# }

# # Tempat menyimpan thread masing-masing sensor
# sensor_threads = {}

# # List log aktivitas
# log_aktivitas = []

# # Log data sensor terakhir
# sensor_data_stream = []

# # Fungsi logging
# def log_event(message: str):
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     log_aktivitas.append(f"[{timestamp}] {message}")

# # Fungsi pembacaan sensor
# def run_sensor(sensor_name: str):
#     while sensor_flags.get(sensor_name, False):
#         if sensor_name == "all":
#             data = baca_sensor()
#         else:
#             data = baca_sensor(sensor_name)

#         sensor_data_stream.append(data)
#         log_event(f"Data dibaca dari {sensor_name.upper()}: {data}")
#         time.sleep(1)

# # Endpoint untuk memulai pembacaan sensor
# @router.post("/sensor/start/{sensor_name}")
# async def start_sensor(sensor_name: str):
#     if sensor_name not in sensor_flags:
#         raise HTTPException(status_code=400, detail="Invalid sensor name")
#     if sensor_flags[sensor_name]:
#         raise HTTPException(status_code=400, detail=f"Sensor {sensor_name} sudah berjalan")

#     sensor_flags[sensor_name] = True
#     thread = Thread(target=run_sensor, args=(sensor_name,))
#     thread.start()
#     sensor_threads[sensor_name] = thread
#     log_event(f"🔵 Sensor {sensor_name.upper()} dimulai")
#     return {"message": f"Sensor {sensor_name} dimulai"}

# # Endpoint untuk menghentikan pembacaan sensor
# @router.post("/sensor/stop/{sensor_name}")
# async def stop_sensor(sensor_name: str):
#     if sensor_name not in sensor_flags:
#         raise HTTPException(status_code=400, detail="Invalid sensor name")
#     if not sensor_flags[sensor_name]:
#         raise HTTPException(status_code=400, detail=f"Sensor {sensor_name} belum berjalan")

#     sensor_flags[sensor_name] = False
#     log_event(f"🔴 Sensor {sensor_name.upper()} dihentikan")
#     return {"message": f"Sensor {sensor_name} dihentikan"}

# # Endpoint untuk mengambil data sensor terakhir
# @router.get("/sensor/stream")
# async def stream_sensor_data():
#     return {"data": sensor_data_stream[-20:]}

# # Endpoint untuk melihat log aktivitas
# @router.get("/sensor/logs")
# async def get_logs():
#     return {"logs": log_aktivitas[-20:]}

# # Endpoint untuk menghapus semua data streaming dan log
# @router.delete("/sensor/clear")
# async def clear_data():
#     sensor_data_stream.clear()
#     log_aktivitas.clear()
#     return {"message": "Data sensor dan log berhasil dibersihkan"}
