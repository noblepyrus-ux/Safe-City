from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.models.sensor import SensorCreate, SensorResponse
from bson import ObjectId

router = APIRouter()

@router.post("/", response_model=SensorResponse, status_code=201)
async def create_sensor(sensor: SensorCreate):
    """Registra un nuevo sensor en la base de datos."""
    db = get_db()
    # Convertir a diccionario para MongoDB
    sensor_dict = sensor.model_dump()
    
    # Insertar en la colección 'sensors'
    result = await db.sensors.insert_one(sensor_dict)
    
    # Recuperar el sensor creado para devolverlo con el ID
    created_sensor = await db.sensors.find_one({"_id": result.inserted_id})
    created_sensor["_id"] = str(created_sensor["_id"]) # Convertir ObjectId a string
    return created_sensor

@router.get("/", response_model=list[SensorResponse])
async def get_sensors():
    """Obtiene la lista de todos los sensores registrados."""
    db = get_db()
    sensors = []
    async for sensor in db.sensors.find():
        sensor["_id"] = str(sensor["_id"])
        sensors.append(sensor)
    return sensors

@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor(sensor_id: str):
    """Obtiene un sensor específico por su ID."""
    db = get_db()
    try:
        sensor = await db.sensors.find_one({"_id": ObjectId(sensor_id)})
        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor no encontrado")
        sensor["_id"] = str(sensor["_id"])
        return sensor
    except Exception:
        raise HTTPException(status_code=400, detail="ID de sensor inválido")