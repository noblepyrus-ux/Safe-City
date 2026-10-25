"""
Router para gestionar las lecturas de nivel de agua de los sensores.
Incluye lógica de evaluación de riesgo y generación automática de alertas.
"""
from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.models.reading import ReadingCreate, ReadingResponse, RiskLevel
from app.models.alert import AlertCreate
from app.config import settings
from bson import ObjectId

router = APIRouter()


@router.post("/", response_model=ReadingResponse, status_code=201)
async def create_reading(reading: ReadingCreate):
    """
    Registra una lectura de nivel de agua.
    Evalúa el riesgo y genera una alerta automática si supera los umbrales.
    """
    db = get_db()
    
    # 1. Validar que el sensor existe
    try:
        sensor = await db.sensors.find_one({"_id": ObjectId(reading.sensor_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID de sensor inválido")
    
    if not sensor:
        raise HTTPException(status_code=404, detail="El sensor no está registrado")

    # 2. Calcular el nivel de riesgo según los umbrales de config.py
    risk_level = RiskLevel.NORMAL
    if reading.water_level >= settings.RISK_THRESHOLD_ALERT:
        risk_level = RiskLevel.DANGER
    elif reading.water_level >= settings.RISK_THRESHOLD_NORMAL:
        risk_level = RiskLevel.ALERT

    # 3. Preparar el documento para MongoDB (convertir sensor_id a ObjectId)
    reading_dict = {
        "sensor_id": ObjectId(reading.sensor_id),  # ← IMPORTANTE: Convertir a ObjectId
        "water_level": reading.water_level,
        "timestamp": reading.timestamp,
        "risk_level": risk_level.value  # ← Guardar el valor del enum, no el objeto
    }
    
    # 4. Insertar en MongoDB
    result = await db.readings.insert_one(reading_dict)

    # 5. Generar alerta automática si hay riesgo
    if risk_level in [RiskLevel.ALERT, RiskLevel.DANGER]:
        alert_dict = {
            "sensor_id": ObjectId(reading.sensor_id),
            "risk_level": risk_level.value,
            "water_level": reading.water_level,
            "message": f"️ ALERTA: Nivel crítico de {reading.water_level}m en {sensor['river_name']} ({sensor['name']})",
            "active": True,
            "created_at": reading.timestamp
        }
        await db.alerts.insert_one(alert_dict)

    # 6. Retornar la lectura con el ID generado
    reading_dict["_id"] = str(result.inserted_id)
    reading_dict["sensor_id"] = str(reading_dict["sensor_id"])  # Convertir de vuelta a string para la respuesta
    return reading_dict


@router.get("/history", response_model=list[ReadingResponse])
async def get_readings_history(sensor_id: str, limit: int = 50):
    """Obtiene el historial de lecturas de un sensor específico."""
    db = get_db()
    readings = []
    
    try:
        cursor = db.readings.find({"sensor_id": ObjectId(sensor_id)}).sort("timestamp", -1).limit(limit)
        
        async for reading in cursor:
            reading["_id"] = str(reading["_id"])
            reading["sensor_id"] = str(reading["sensor_id"])
            readings.append(reading)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al consultar lecturas: {str(e)}")
    
    return readings


@router.get("/latest", response_model=ReadingResponse)
async def get_latest_reading(sensor_id: str):
    """Obtiene la última lectura de un sensor específico."""
    db = get_db()
    
    try:
        reading = await db.readings.find_one({"sensor_id": ObjectId(sensor_id)}, sort=[("timestamp", -1)])
    except Exception:
        raise HTTPException(status_code=400, detail="ID de sensor inválido")
    
    if not reading:
        raise HTTPException(status_code=404, detail="No hay lecturas registradas para este sensor")
    
    reading["_id"] = str(reading["_id"])
    reading["sensor_id"] = str(reading["sensor_id"])
    return reading