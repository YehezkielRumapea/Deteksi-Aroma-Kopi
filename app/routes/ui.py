from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.database import get_db
from sqlalchemy.orm import Session
from app.models import SensorData
from app.routes.sensor import get_latest_sensor_data, get_api_logs

router = APIRouter()

# Konfigurasi templates dan static files
templates = Jinja2Templates(directory="app/templates")

# Tambahkan static files agar bisa diakses di frontend
router.mount("/static", StaticFiles(directory="app/static"), name="static")

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = next(get_db())):
    sensor_data = get_latest_sensor_data(db)
    api_logs = get_api_logs(db)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "sensor_data": sensor_data,
        "api_logs": api_logs
    })
