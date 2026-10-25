"""
Modelos Pydantic para las lecturas de nivel de agua.
"""
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from datetime import datetime
from typing import Optional  # <-- ¡ESTA ERA LA LÍNEA FALTANTE!
from typing_extensions import Annotated
from pydantic.functional_validators import BeforeValidator
from enum import Enum

PyObjectId = Annotated[str, BeforeValidator(str)]


class RiskLevel(str, Enum):
    """Niveles de riesgo de inundación."""
    NORMAL = "normal"
    ALERT = "alerta"
    DANGER = "peligro"


class ReadingBase(BaseModel):
    """Esquema base de una lectura."""
    sensor_id: PyObjectId = Field(..., description="ID del sensor que genera la lectura")
    water_level: float = Field(..., gt=0, description="Nivel del agua en metros")


class ReadingCreate(ReadingBase):
    """Esquema para crear una nueva lectura."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadingResponse(ReadingBase):
    """Esquema de respuesta de una lectura."""
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    timestamp: datetime
    risk_level: RiskLevel = Field(..., description="Nivel de riesgo calculado")