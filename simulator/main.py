import os
import time
import random
import requests
from datetime import datetime, timezone

# Configuración desde variables de entorno
BACKEND_URL = os.getenv("BACKEND_URL", "http://safe-city-api:8000") # Cambiado a nombre del servicio Docker
INTERVAL = int(os.getenv("SIMULATION_INTERVAL", "5"))

# Credenciales del admin para que el simulador pueda registrarse
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")
TOKEN = ""

# Configuración de sensores simulados (Ríos de Bogotá como ejemplo)
SENSORS = [
    {"name": "Sensor Puente Aranda", "river": "Río Bogotá", "base_level": 1.5, "sensor_id": None},
    {"name": "Sensor La Calera", "river": "Quebrada La Vieja", "base_level": 1.2, "sensor_id": None},
    {"name": "Sensor Bosa", "river": "Río Fucha", "base_level": 1.8, "sensor_id": None},
    {"name": "Sensor Usme", "river": "Quebrada San Cristóbal", "base_level": 1.0, "sensor_id": None},
]

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
    """Espera a que el backend esté listo antes de continuar."""
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

def register_sensors():
    """Registra los sensores en la API y guarda sus IDs."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    for sensor in SENSORS:
        payload = {
            "name": sensor["name"],
            "river_name": sensor["river"],
            "location": {"lat": 4.6097 + random.uniform(-0.1, 0.1), "lng": -74.0817 + random.uniform(-0.1, 0.1)},
        }
        try:
            response = requests.post(f"{BACKEND_URL}/sensors/", json=payload, headers=headers)
            if response.status_code == 201:
                sensor["sensor_id"] = response.json()["_id"]
                print(f"  ✅ Registrado: {sensor['name']} (ID: {sensor['sensor_id'][:8]}...)")
            elif response.status_code == 400 and "ya está registrado" in response.text:
                print(f"  ℹ️ Ya existe: {sensor['name']}")
                # Si ya existe, necesitamos obtener su ID. Hacemos un GET para buscarlo.
                get_res = requests.get(f"{BACKEND_URL}/sensors/", headers=headers)
                if get_res.status_code == 200:
                    for s in get_res.json():
                        if s["name"] == sensor["name"]:
                            sensor["sensor_id"] = s["_id"]
                            break
            else:
                print(f"  ⚠️ Error registrando {sensor['name']}: {response.text}")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Error de conexión al registrar {sensor['name']}")

def simulate_readings():
    """Envía lecturas de nivel de agua periódicamente."""
    print(f"\n🌊 Iniciando simulación de lecturas cada {INTERVAL} segundos...")
    print("Presiona Ctrl+C en la terminal principal para detener todo.\n")
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    while True:
        for sensor in SENSORS:
            if not sensor["sensor_id"]:
                continue
                
            # Variación normal del agua (±0.2m)
            water_level = sensor["base_level"] + random.uniform(-0.2, 0.2)
            
            # 15% de probabilidad de una crecida repentina (para generar alertas)
            if random.random() < 0.15:
                water_level += random.uniform(1.0, 2.5)  # Pico de agua
                
            water_level = round(max(0.5, water_level), 2) # Mínimo 0.5m
            
            payload = {
                "sensor_id": sensor["sensor_id"],
                "water_level": water_level,
            }
            
            try:
                response = requests.post(f"{BACKEND_URL}/readings/", json=payload, headers=headers)
                if response.status_code == 201:
                    data = response.json()
                    risk = data["risk_level"].upper()
                    emoji = "🟢" if risk == "NORMAL" else "🟡" if risk == "ALERTA" else "🔴"
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {emoji} {sensor['river']} ({sensor['name']}): {water_level}m - Riesgo: {risk}")
            except requests.exceptions.ConnectionError:
                print("  ⚠️ Perdida temporal de conexión con el backend.")
                
        time.sleep(INTERVAL)

if __name__ == "__main__":
    if wait_for_backend():
        if login():
            register_sensors()
            simulate_readings()
        else:
            print("❌ No se pudo autenticar. Saliendo.")
            exit(1)
    else:
        print("❌ Backend no disponible. Saliendo.")
        exit(1)