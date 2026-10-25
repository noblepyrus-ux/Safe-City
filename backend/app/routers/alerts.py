from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.models.alert import AlertResponse
from bson import ObjectId

router = APIRouter()

@router.get("/", response_model=list[AlertResponse])
async def get_active_alerts():
    """Obtiene todas las alertas que están actualmente activas."""
    db = get_db()
    alerts = []
    cursor = db.alerts.find({"active": True}).sort("created_at", -1)
    
    async for alert in cursor:
        alert["_id"] = str(alert["_id"])
        alerts.append(alert)
    return alerts

@router.get("/history", response_model=list[AlertResponse])
async def get_all_alerts():
    """Obtiene el historial completo de alertas (activas y resueltas)."""
    db = get_db()
    alerts = []
    cursor = db.alerts.find().sort("created_at", -1).limit(100)
    
    async for alert in cursor:
        alert["_id"] = str(alert["_id"])
        alerts.append(alert)
    return alerts