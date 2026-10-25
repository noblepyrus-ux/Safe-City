"""
Safe City API - Aplicación principal FastAPI.
Sistema de monitoreo de ríos y detección temprana de inundaciones.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import connect_to_mongo, close_mongo_connection
from app.config import settings

# Importar los routers
from app.routers import sensors, readings, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.API_TITLE,
    description="Sistema de monitoreo de ríos y detección temprana de inundaciones",
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configuración de CORS para permitir el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar los routers con sus prefijos
app.include_router(sensors.router, prefix="/sensors", tags=["Sensores IoT"])
app.include_router(readings.router, prefix="/readings", tags=["Lecturas y Riesgo"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alertas Tempranas"])


@app.get("/")
async def root():
    """Endpoint principal para verificar el estado del servicio."""
    return {
        "status": "ok",
        "service": "Safe City API",
        "version": settings.API_VERSION
    }


@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud para Docker y monitoreo."""
    return {"status": "healthy"}


@app.get("/config")
async def get_config():
    """Endpoint para verificar la configuración activa (sin credenciales)."""
    return {
        "mongo_db": settings.MONGO_DB,
        "risk_thresholds": {
            "normal": settings.RISK_THRESHOLD_NORMAL,
            "alert": settings.RISK_THRESHOLD_ALERT
        }
    }