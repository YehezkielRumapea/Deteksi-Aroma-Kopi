from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import SensorData
import json
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import httpx

router = APIRouter(prefix="/sensor", tags=["sensor"])
logger = logging.getLogger(__name__)
active_connections = []

@router.get("/latest")
async def get_latest_sensor_data(db: Session = Depends(get_db)):
    latest_data = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
    if latest_data:
        ai_classification_json = {}
        if latest_data.ai_classification:
            try:
                ai_classification_json = json.loads(latest_data.ai_classification)
            except json.JSONDecodeError:
                ai_classification_json = {"raw": latest_data.ai_classification}
        return {
            "id": latest_data.id,
            "timestamp": latest_data.timestamp.isoformat(),
            "mq135": latest_data.mq135,
            "mq2": latest_data.mq2,
            "mq4": latest_data.mq4,
            "mq7": latest_data.mq7,
            "jenis": latest_data.jenis,
            "ai_classification": ai_classification_json
        }
    return {"error": "No data available"}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    try:
        await websocket.accept()
        logger.info("WebSocket connection opened")
        active_connections.append(websocket)
        last_data_id = None
        while True:
            latest_data = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
            if latest_data:
                current_data_id = latest_data.id
                if last_data_id != current_data_id:
                    last_data_id = current_data_id
                    ai_classification_json = {}
                    if latest_data.ai_classification:
                        try:
                            ai_classification_json = json.loads(latest_data.ai_classification)
                        except json.JSONDecodeError:
                            ai_classification_json = {"raw": latest_data.ai_classification}
                    await websocket.send_json({
                        "timestamp": latest_data.timestamp.isoformat(),
                        "mq135": latest_data.mq135,
                        "mq2": latest_data.mq2,
                        "mq4": latest_data.mq4,
                        "mq7": latest_data.mq7,
                        "jenis": latest_data.jenis,
                        "ai_classification": ai_classification_json
                    })
            else:
                await websocket.send_json({"error": "No sensor data available"})
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
        active_connections.remove(websocket)
    finally:
        await websocket.close()

@router.post("/classification")
async def save_classification(classification: dict, db: Session = Depends(get_db)):
    try:
        logger.info(f"Received classification: {classification}")
        required_keys = {"type", "confidence", "composition"}
        if not all(key in classification for key in required_keys):
            logger.error(f"Invalid classification format: Missing keys")
            return {"status": "error", "message": f"Missing required keys"}
        classification_json = {
            "type": classification.get("type"),
            "confidence": classification.get("confidence"),
            "composition": classification.get("composition")
        }
        latest_sensor = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
        if not latest_sensor:
            logger.error("No sensor data found to update classification")
            return {"status": "error", "message": "No sensor data available"}
        latest_sensor.ai_classification = json.dumps(classification_json)
        db.commit()
        db.refresh(latest_sensor)
        logger.info(f"Updated ai_classification for sensor ID {latest_sensor.id}")
        return {"status": "success", "message": "Classification saved"}
    except Exception as e:
        logger.error(f"Error saving classification: {e}")
        return {"status": "error", "message": str(e)}

@router.delete("/delete")
async def delete_sensor_data(db: Session = Depends(get_db)):
    try:
        deleted_rows = db.query(SensorData).delete()
        db.commit()
        logger.info(f"Deleted {deleted_rows} sensor data entries")
        return {"message": f"Deleted {deleted_rows} sensor data entries successfully"}
    except Exception as e:
        logger.error(f"Failed to delete data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete data: {e}")

@router.get("/data/db/{interval}")
async def get_sensor_data(interval: str, db: Session = Depends(get_db)):
    try:
        now = datetime.now(pytz.timezone('Asia/Jakarta'))
        if interval == "3s":
            time_delta = timedelta(seconds=30)  # 30 detik terakhir
        elif interval == "10s":
            time_delta = timedelta(seconds=60)  # 1 menit terakhir
        elif interval == "30s":
            time_delta = timedelta(seconds=180)  # 3 menit terakhir
        elif interval == "1min":
            time_delta = timedelta(minutes=1)  # 1 menit terakhir
        elif interval == "5min":
            time_delta = timedelta(minutes=5)  # 5 menit terakhir
        else:
            raise HTTPException(status_code=400, detail="Invalid interval")
        data = db.query(SensorData).filter(
            SensorData.timestamp >= now - time_delta
        ).order_by(SensorData.timestamp.asc()).all()
        result = []
        for d in data:
            ai_classification_json = {}
            if d.ai_classification:
                try:
                    ai_classification_json = json.loads(d.ai_classification)
                except json.JSONDecodeError:
                    ai_classification_json = {"raw": d.ai_classification}
            result.append({
                "timestamp": d.timestamp.isoformat(),
                "mq135": d.mq135,
                "mq2": d.mq2,
                "mq4": d.mq4,
                "mq7": d.mq7,
                "jenis": d.jenis,
                "ai_classification": ai_classification_json
            })
        logger.info(f"Fetched {len(result)} data points for interval {interval}")
        return result
    except Exception as e:
        logger.error(f"Error fetching sensor data for interval {interval}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start-ai")
async def start_ai():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://192.168.129.105:8001/start-ai")
            response.raise_for_status()
            result = response.json()
            if result["status"] == "error":
                logger.error(f"AI script error: {result['message']}")
                return {"status": "error", "message": result["message"]}
            logger.info(f"AI script success: {result['message']}")
            return {"status": "success", "message": "AI berhasil dijalankan"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling AI server: {e}")
        return {"status": "error", "message": f"Error komunikasi dengan AI server: {str(e)}"}
    except Exception as e:
        logger.error(f"Error starting AI: {e}")
        return {"status": "error", "message": f"Error memulai AI: {str(e)}"}

@router.post("/stop-ai")
async def stop_ai():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://192.168.129.105:8001/stop-ai")
            response.raise_for_status()
            result = response.json()
            if result["status"] == "error":
                logger.error(f"AI script error: {result['message']}")
                return {"status": "error", "message": result["message"]}
            logger.info(f"AI script success: {result['message']}")
            return {"status": "success", "message": "AI berhasil dihentikan"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling AI server: {e}")
        return {"status": "error", "message": f"Error komunikasi dengan AI server: {str(e)}"}
    except Exception as e:
        logger.error(f"Error stopping AI: {e}")
        return {"status": "error", "message": f"Error menghentikan AI: {str(e)}"}