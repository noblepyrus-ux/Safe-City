"""
Modelos Pydantic para las alertas de inundación.
"""
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from datetime import datetime
from typing import Optional
from typing_extensions import Annotated
from pydantic.functional_validators import BeforeValidator
from app.models.reading import RiskLevel

PyObjectId = Annotated[str, BeforeValidator(str)]


class AlertBase(BaseModel):
    """Esquema base de una alerta."""
    sensor_id: PyObjectId = Field(..., description="ID del sensor que generó la alerta")
    risk_level: RiskLevel = Field(..., description="Nivel de riesgo")
    water_level: float = Field(..., description="Nivel del agua en metros al momento de la alerta")
    message: str = Field(..., description="Mensaje descriptivo de la alerta")


class AlertCreate(AlertBase):
    """Esquema para crear una nueva alerta."""
    active: bool = Field(default=True, description="Indica si la alerta está activa")


class AlertResponse(AlertBase):
    """Esquema de respuesta de una alerta."""
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    active: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(default=None, description="Fecha de resolución")