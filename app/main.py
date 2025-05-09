import time
import threading
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_db
from app.routes.sensor import router as sensor_router
from app.services import sensor_service
from app.services.sensor_reader import baca_sensor
from app.schemas.sensor import SensorCreate
from fastapi.responses import HTMLResponse

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(sensor_router)
templates = Jinja2Templates(directory="app/templates")

# Status dan thread untuk setiap sensor
sensor_status = {
    "mq135": threading.Event(),
    "mq2": threading.Event(),
    "mq4": threading.Event(),
    "mq7": threading.Event(),
    "all": threading.Event()
}
sensor_threads = {
    "mq135": None,
    "mq2": None,
    "mq4": None,
    "mq7": None,
    "all": None
}

def sensor_loop(sensor_name: str):
    while True:
        if not sensor_status[sensor_name].is_set():
            break
        db = SessionLocal()
        try:
            sensor_data = baca_sensor(sensor_name if sensor_name != "all" else None)
            sensor_data["kualitas"] = sensor_service.tentukan_kualitas(sensor_data)
            sensor_model = SensorCreate(**{
                "mq135": float(sensor_data["mq135"]) if sensor_data.get("mq135") else None,
                "mq2": float(sensor_data["mq2"]) if sensor_data.get("mq2") else None,
                "mq4": float(sensor_data["mq4"]) if sensor_data.get("mq4") else None,
                "mq7": float(sensor_data["mq7"]) if sensor_data.get("mq7") else None,
                "kualitas": sensor_data["kualitas"]
            })
            sensor_service.create_sensor_data(db, sensor_model)
            print(f"✅ Data {sensor_name} tersimpan: {sensor_data}")
        except Exception as e:
            print(f"❌ Gagal menyimpan data {sensor_name}: {e}")
        finally:
            db.close()
        time.sleep(3)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("dashboard.html", {
        "request": request
    })

@app.post("/sensor/start/{sensor}")
def start_sensor(sensor: str, db: Session = Depends(get_db)):
    if sensor not in sensor_status:
        return {"error": f"Sensor {sensor} tidak valid"}
    
    # Hentikan semua sensor lain jika "all" dipilih
    if sensor == "all":
        for s in ["mq135", "mq2", "mq4", "mq7"]:
            sensor_status[s].clear()
            if sensor_threads[s]:
                sensor_threads[s].join(timeout=5.0)
                sensor_threads[s] = None
    else:
        # Hentikan mode "all" jika sensor individu dipilih
        sensor_status["all"].clear()
        if sensor_threads["all"]:
            sensor_threads["all"].join(timeout=5.0)
            sensor_threads["all"] = None
    
    if sensor_status[sensor].is_set():
        return {"message": f"Sensor {sensor.upper()} sudah berjalan!"}
    
    sensor_status[sensor].set()
    sensor_threads[sensor] = threading.Thread(target=sensor_loop, args=(sensor,), daemon=True)
    sensor_threads[sensor].start()
    return {"message": f"Sensor {sensor.upper()} mulai mengambil data!"}

@app.post("/sensor/stop/{sensor}")
def stop_sensor(sensor: str, db: Session = Depends(get_db)):
    if sensor not in sensor_status:
        return {"error": f"Sensor {sensor} tidak valid"}
    
    sensor_status[sensor].clear()
    if sensor_threads[sensor]:
        sensor_threads[sensor].join(timeout=5.0)
        sensor_threads[sensor] = None
    return {"message": f"Sensor {sensor.upper()} berhenti mengambil data!"}

@app.post("/sensor/stop")
def stop_all_sensors(db: Session = Depends(get_db)):
    for sensor in sensor_status:
        sensor_status[sensor].clear()
        if sensor_threads[sensor]:
            sensor_threads[sensor].join(timeout=5.0)
            sensor_threads[sensor] = None
    return {"message": "Semua sensor berhenti mengambil data!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)