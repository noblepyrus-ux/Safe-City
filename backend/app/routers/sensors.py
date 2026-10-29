from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.models.sensor import SensorCreate, SensorResponse
from bson import ObjectId
from app.services.auth import get_current_user, require_role
from app.models.user import UserRole
from datetime import datetime

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
    # ¡IMPORTANTE: async for es obligatorio con Motor!
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

@router.put("/{sensor_id}", response_model=SensorResponse)
async def update_sensor(
    sensor_id: str,
    sensor_update: dict,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db=Depends(get_db)
):
    """Actualiza un sensor existente (solo admin)."""
    try:
        result = await db.sensors.update_one(
            {"_id": ObjectId(sensor_id)},
            {
                "$set": {
                    "name": sensor_update.get("name"),
                    "river_name": sensor_update.get("river_name"),
                    "location": sensor_update.get("location"),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Sensor no encontrado")
        
        updated = await db.sensors.find_one({"_id": ObjectId(sensor_id)})
        updated["_id"] = str(updated["_id"])
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al actualizar: {str(e)}")


@router.delete("/{sensor_id}")
async def delete_sensor(
    sensor_id: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db=Depends(get_db)
):
    """Elimina un sensor y sus lecturas (solo admin)."""
    try:
        # Eliminar sensor
        result = await db.sensors.delete_one({"_id": ObjectId(sensor_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Sensor no encontrado")
        
        # Eliminar lecturas y alertas asociadas
        await db.readings.delete_many({"sensor_id": ObjectId(sensor_id)})
        await db.alerts.delete_many({"sensor_id": ObjectId(sensor_id)})
        
        return {"message": "Sensor eliminado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al eliminar: {str(e)}")