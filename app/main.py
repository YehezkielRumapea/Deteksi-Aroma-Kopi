import time
import threading
import os
from datetime import datetime
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_db
from app.routes.sensor import router as sensor_router
from app.services import sensor_service
from app.services.sensor_reader import baca_sensor, start_sensor, stop_sensor, stop_all_sensors
from app.schemas.sensor import SensorCreate
from fastapi.responses import HTMLResponse
import logging
from app.config import sensor_status, sensor_threads
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(sensor_router)
templates = Jinja2Templates(directory="app/templates")

# Thread untuk ekspor
export_thread = None

def sensor_loop(sensor_name: str):
    while True:
        if not sensor_status[sensor_name].is_set():
            break
        db = SessionLocal()
        try:
            sensor_data = baca_sensor(sensor_name if sensor_name != "all" else None)
            sensor_data["jenis"] = sensor_service.tentukan_jenis(sensor_data)
            sensor_model = SensorCreate(**{
                "timestamp": sensor_data["timestamp"],
                "mq135": float(sensor_data["mq135"]) if sensor_data.get("mq135") else None,
                "mq2": float(sensor_data["mq2"]) if sensor_data.get("mq2") else None,
                "mq4": float(sensor_data["mq4"]) if sensor_data.get("mq4") else None,
                "mq7": float(sensor_data["mq7"]) if sensor_data.get("mq7") else None,
                "jenis": sensor_data["jenis"]
            })
            sensor_service.create_sensor_data(db, sensor_model)
            logger.info(f"✅ Data {sensor_name} tersimpan: {sensor_data}")
        except Exception as e:
            logger.error(f"❌ Gagal menyimpan data {sensor_name}: {e}")
        finally:
            db.close()
        time.sleep(1)

def export_loop():
    db = SessionLocal()
    output_dir = "/home/Yehezkiel/E-Nose-Backend/data"
    os.makedirs(output_dir, exist_ok=True)
    while True:
        if not any(sensor_status[s].is_set() for s in sensor_status):
            break
        try:
            result = sensor_service.export_sensor_data_to_csv(db, output_dir)
            logger.info(f"✅ {result['message']}")
        except Exception as e:
            logger.error(f"❌ Gagal ekspor data: {e}")
        time.sleep(600)
    db.close()

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    api_logs = sensor_service.get_logs_api(db)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "api_logs": api_logs
    })

@app.post("/sensor/start/{sensor}")
async def start_sensor_endpoint(sensor: str, db: Session = Depends(get_db)):
    global export_thread
    if sensor not in sensor_status:
        return {"error": f"Sensor {sensor} tidak valid"}

    # Jika "all" dimulai, hentikan semua sensor individu
    if sensor == "all":
        for s in ["mq135", "mq2", "mq4", "mq7"]:
            if sensor_status[s].is_set():
                stop_sensor(s)
                sensor_status[s].clear()
                if sensor_threads[s]:
                    sensor_threads[s].join(timeout=5.0)
                    sensor_threads[s] = None
    else:
        # Jika sensor individu dimulai, hentikan "all"
        if sensor_status["all"].is_set():
            stop_sensor("all")
            sensor_status["all"].clear()
            if sensor_threads["all"]:
                sensor_threads["all"].join(timeout=5.0)
                sensor_threads["all"] = None

    if sensor_status[sensor].is_set():
        return {"message": f"Sensor {sensor.upper()} sudah berjalan!"}

    try:
        start_sensor(sensor)
        sensor_status[sensor].set()
        sensor_threads[sensor] = threading.Thread(target=sensor_loop, args=(sensor,), daemon=True)
        sensor_threads[sensor].start()
    except Exception as e:
        logger.error(f"❌ Gagal memulai sensor {sensor}: {e}")
        return {"error": f"Gagal memulai sensor: {e}"}

    if not export_thread or not export_thread.is_alive():
        export_thread = threading.Thread(target=export_loop, daemon=True)
        export_thread.start()

    logger.info(f"Sensor {sensor.upper()} dimulai")
    return {"message": f"Sensor {sensor.upper()} mulai mengambil data!"}

@app.post("/sensor/stop/{sensor}")
async def stop_sensor_endpoint(sensor: str, db: Session = Depends(get_db)):
    if sensor not in sensor_status:
        return {"error": f"Sensor {sensor} tidak valid"}

    try:
        stop_sensor(sensor)
        sensor_status[sensor].clear()
        if sensor_threads[sensor]:
            sensor_threads[sensor].join(timeout=5.0)
            sensor_threads[sensor] = None
        logger.info(f"Sensor {sensor.upper()} dihentikan")
        return {"message": f"Sensor {sensor.upper()} berhenti mengambil data!"}
    except Exception as e:
        logger.error(f"❌ Gagal menghentikan sensor {sensor}: {e}")
        return {"error": f"Gagal menghentikan sensor: {e}"}

@app.post("/sensor/stop")
async def stop_all_sensors_endpoint(db: Session = Depends(get_db)):
    try:
        stop_all_sensors()
        for sensor in sensor_status:
            sensor_status[sensor].clear()
            if sensor_threads[sensor]:
                sensor_threads[sensor].join(timeout=5.0)
                sensor_threads[sensor] = None
        logger.info("Semua sensor dihentikan")
        return {"message": "Semua sensor berhenti mengambil data!"}
    except Exception as e:
        logger.error(f"❌ Gagal menghentikan semua sensor: {e}")
        return {"error": f"Gagal menghentikan semua sensor: {e}"}

# Konfigurasi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.129.105", "http://192.168.129.215", "ws://192.168.129.215:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)