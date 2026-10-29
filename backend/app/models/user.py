"""
Modelos Pydantic para usuarios y autenticación.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class UserRole(str, Enum):
    """Roles disponibles en el sistema."""
    ADMIN = "admin"
    VIEWER = "viewer"


class UserBase(BaseModel):
    """Esquema base del usuario."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    """Esquema para crear un nuevo usuario (incluye contraseña en texto plano)."""
    password: str = Field(..., min_length=6, max_length=100)


class UserResponse(UserBase):
    """Esquema de respuesta del usuario (sin contraseña)."""
    id: Optional[str] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        populate_by_name = True


class UserLogin(BaseModel):
    """Esquema para el login."""
    username: str
    password: str


class Token(BaseModel):
    """Esquema del token JWT."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Datos dentro del token JWT."""
    username: Optional[str] = None
    role: Optional[str] = None