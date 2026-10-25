"""
Modelos Pydantic para los sensores IoT de monitoreo de ríos.
"""
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from typing import Optional
from datetime import datetime
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated

# Tipo personalizado para manejar ObjectId de MongoDB en Pydantic v2
PyObjectId = Annotated[str, BeforeValidator(str)]


class Location(BaseModel):
    """Coordenadas geográficas del sensor."""
    lat: float = Field(..., ge=-90, le=90, description="Latitud")
    lng: float = Field(..., ge=-180, le=180, description="Longitud")


class SensorBase(BaseModel):
    """Esquema base del sensor."""
    name: str = Field(..., min_length=3, max_length=50, description="Nombre del sensor")
    river_name: str = Field(..., min_length=3, max_length=50, description="Nombre del río o quebrada")
    location: Location = Field(..., description="Ubicación geográfica")


class SensorCreate(SensorBase):
    """Esquema para crear un nuevo sensor."""
    installed_date: Optional[datetime] = Field(default_factory=datetime.utcnow)


class SensorResponse(SensorBase):
    """Esquema de respuesta del sensor (incluye ID y timestamps)."""
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    installed_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)