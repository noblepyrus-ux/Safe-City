from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.models.sensor import SensorCreate, SensorResponse
from bson import ObjectId
from app.services.auth import get_current_user, require_role
from app.models.user import UserRole

router = APIRouter()

@router.post("/", response_model=SensorResponse, status_code=201)
async def create_sensor(
    sensor: SensorCreate,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db=Depends(get_db)
):
    """Registra un nuevo sensor en la base de datos. Solo ADMIN puede crear."""
    sensor_dict = sensor.model_dump()
    
    result = await db.sensors.insert_one(sensor_dict)
    
    created_sensor = await db.sensors.find_one({"_id": result.inserted_id})
    created_sensor["_id"] = str(created_sensor["_id"])
    return created_sensor

@router.get("/", response_model=list[SensorResponse])
async def get_sensors(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """Obtiene la lista de todos los sensores registrados. Requiere autenticación."""
    sensors = []
    async for sensor in db.sensors.find():
        sensor["_id"] = str(sensor["_id"])
        sensors.append(sensor)
    return sensors

@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor(
    sensor_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """Obtiene un sensor específico por su ID. Requiere autenticación."""
    try:
        sensor = await db.sensors.find_one({"_id": ObjectId(sensor_id)})
        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor no encontrado")
        sensor["_id"] = str(sensor["_id"])
        return sensor
    except Exception:
        raise HTTPException(status_code=400, detail="ID de sensor inválido")