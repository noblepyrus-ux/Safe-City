"""
Configuración centralizada del proyecto Safe City.
Usa pydantic-settings para cargar variables de entorno de forma segura.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuración global de la aplicación."""
    
    # Configuración de MongoDB
    MONGO_URI: str = "mongodb://mongo:27017"
    MONGO_DB: str = "safe_city"
    
    # Configuración de la API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "Safe City API"
    API_VERSION: str = "1.0.0"
    
    # Umbrales de riesgo para inundaciones (en metros)
    RISK_THRESHOLD_NORMAL: float = 2.0
    RISK_THRESHOLD_ALERT: float = 3.0
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de settings para reutilizar en toda la app
settings = Settings()