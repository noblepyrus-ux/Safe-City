import os
import time
import random
import requests
from datetime import datetime

# Configuración desde variables de entorno
BACKEND_URL = os.getenv("BACKEND_URL", "http://safe-city-api:8000")
INTERVAL = int(os.getenv("SIMULATION_INTERVAL", "5"))

# Credenciales del admin
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")
TOKEN = ""

# Sensores base (solo para inicialización si la BD está vacía)
DEFAULT_SENSORS = [
    {"name": "Sensor Puente Aranda", "river": "Río Bogotá", "base_level": 1.5},
    {"name": "Sensor La Calera", "river": "Quebrada La Vieja", "base_level": 1.2},
    {"name": "Sensor Bosa", "river": "Río Fucha", "base_level": 1.8},
    {"name": "Sensor Usme", "river": "Quebrada San Cristóbal", "base_level": 1.0},
]

# Almacén de sensores activos con sus IDs
ACTIVE_SENSORS = []

def login():
    """Inicia sesión para obtener el token JWT."""
    global TOKEN
    print("🔑 Intentando autenticar al simulador...")
    try:
        response = requests.post(f"{BACKEND_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        if response.status_code == 200:
            TOKEN = response.json()["access_token"]
            print("✅ ¡Simulador autenticado exitosamente!")
            return True
        else:
            print(f"❌ Error de autenticación: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ No se pudo conectar al backend para autenticar: {e}")
        return False

def wait_for_backend():
    """Espera a que el backend esté listo."""
    print("📡 Esperando a que el backend esté disponible...")
    max_retries = 15
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✅ ¡Backend listo!")
                return True
        except requests.exceptions.RequestException:
            print(f"⏳ Backend no disponible. Reintentando en 3s... ({attempt + 1}/{max_retries})")
            time.sleep(3)
    return False

def get_all_sensors():
    """Obtiene todos los sensores de la base de datos."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        response = requests.get(f"{BACKEND_URL}/sensors/", headers=headers)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error obteniendo sensores: {e}")
    return []

def create_default_sensors():
    """Crea los sensores por defecto SOLO si no existen."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # Primero obtener los sensores existentes
    existing_sensors = get_all_sensors()
    existing_names = {s["name"] for s in existing_sensors}
    
    created = []
    for sensor in DEFAULT_SENSORS:
        # Solo crear si no existe
        if sensor["name"] in existing_names:
            print(f"  ℹ️ Ya existe: {sensor['name']}")
            # Buscar el sensor existente
            for s in existing_sensors:
                if s["name"] == sensor["name"]:
                    s["base_level"] = sensor["base_level"]
                    created.append(s)
                    break
        else:
            # Crear el sensor
            payload = {
                "name": sensor["name"],
                "river_name": sensor["river"],
                "location": {"lat": 4.6097 + random.uniform(-0.1, 0.1), "lng": -74.0817 + random.uniform(-0.1, 0.1)},
            }
            try:
                response = requests.post(f"{BACKEND_URL}/sensors/", json=payload, headers=headers)
                if response.status_code == 201:
                    sensor_data = response.json()
                    sensor_data["base_level"] = sensor["base_level"]
                    created.append(sensor_data)
                    print(f"  ✅ Creado: {sensor['name']}")
                else:
                    print(f"  ⚠️ Error creando {sensor['name']}: {response.text}")
            except requests.exceptions.ConnectionError:
                print(f"  ❌ Error de conexión al crear {sensor['name']}")
    
    return created

def sync_sensors():
    """Sincroniza la lista de sensores activos con la base de datos."""
    global ACTIVE_SENSORS
    
    # Obtener sensores de la BD
    db_sensors = get_all_sensors()
    
    if not db_sensors:
        print("⚠️ No hay sensores en la BD. Creando sensores por defecto...")
        db_sensors = create_default_sensors()
    
    # Actualizar ACTIVE_SENSORS con los sensores de la BD
    # Mantener base_level si ya existía, sino usar valor por defecto
    old_levels = {s["name"]: s.get("base_level", 1.5) for s in ACTIVE_SENSORS}
    
    ACTIVE_SENSORS = []
    for s in db_sensors:
        # Buscar si es un sensor por defecto para asignarle el base_level correcto
        base_level = old_levels.get(s["name"], 1.5)
        for default in DEFAULT_SENSORS:
            if default["name"] == s["name"]:
                base_level = default["base_level"]
                break
        
        ACTIVE_SENSORS.append({
            "_id": s["_id"],
            "name": s["name"],
            "river": s.get("river_name", "Río desconocido"),
            "base_level": base_level
        })
    
    print(f"🔄 Sensores activos sincronizados: {len(ACTIVE_SENSORS)}")
    for s in ACTIVE_SENSORS:
        print(f"   - {s['name']} ({s['river']}) - Base: {s['base_level']}m")

def simulate_readings():
    """Envía lecturas de nivel de agua periódicamente para todos los sensores activos."""
    print(f"\n🌊 Iniciando simulación de lecturas cada {INTERVAL} segundos...")
    print("Presiona Ctrl+C en la terminal principal para detener todo.\n")
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    sync_counter = 0
    
    while True:
        # Sincronizar sensores cada 30 segundos (para detectar nuevos sensores agregados)
        sync_counter += 1
        if sync_counter >= 6:  # Cada 30 segundos (6 * 5s)
            sync_sensors()
            sync_counter = 0
        
        for sensor in ACTIVE_SENSORS:
            # Variación normal del agua (±0.2m)
            water_level = sensor["base_level"] + random.uniform(-0.2, 0.2)
            
            # 15% de probabilidad de una crecida repentina
            if random.random() < 0.15:
                water_level += random.uniform(1.0, 2.5)
                
            water_level = round(max(0.5, water_level), 2)
            
            payload = {
                "sensor_id": sensor["_id"],
                "water_level": water_level,
            }
            
            try:
                response = requests.post(f"{BACKEND_URL}/readings/", json=payload, headers=headers)
                if response.status_code == 201:
                    data = response.json()
                    risk = data["risk_level"].upper()
                    emoji = "" if risk == "NORMAL" else "" if risk == "ALERTA" else "🔴"
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {emoji} {sensor['river']} ({sensor['name']}): {water_level}m - Riesgo: {risk}")
                elif response.status_code == 401:
                    print("⚠️ Token expirado. Reautenticando...")
                    if login():
                        headers = {"Authorization": f"Bearer {TOKEN}"}
            except requests.exceptions.ConnectionError:
                print("  ⚠️ Perdida temporal de conexión con el backend.")
                
        time.sleep(INTERVAL)

if __name__ == "__main__":
    if wait_for_backend():
        if login():
            sync_sensors()  # Cargar sensores iniciales
            simulate_readings()
        else:
            print(" No se pudo autenticar. Saliendo.")
            exit(1)
    else:
        print("❌ Backend no disponible. Saliendo.")
        exit(1)