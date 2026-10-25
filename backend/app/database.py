"""
Módulo de conexión a MongoDB usando Motor (driver asíncrono oficial).
Gestiona el ciclo de vida de la conexión (abrir/cerrar).
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.config import settings

# Cliente global de MongoDB (se inicializa en el startup)
db_client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo() -> None:
    """Establece la conexión con MongoDB al iniciar la aplicación."""
    global db_client
    try:
        db_client = AsyncIOMotorClient(settings.MONGO_URI)
        # Verificar conexión haciendo ping
        await db_client.admin.command("ping")
        print(f"✅ Conectado exitosamente a MongoDB: {settings.MONGO_DB}")
    except Exception as e:
        print(f"❌ Error al conectar con MongoDB: {e}")
        raise


async def close_mongo_connection() -> None:
    """Cierra la conexión con MongoDB al detener la aplicación."""
    global db_client
    if db_client:
        db_client.close()
        print(" Conexión con MongoDB cerrada")


def get_db():
    """
    Helper para obtener la base de datos.
    Usar como dependencia en los routers.
    """
    if db_client is None:
        raise RuntimeError("MongoDB no está conectado. Inicia la aplicación primero.")
    return db_client[settings.MONGO_DB]