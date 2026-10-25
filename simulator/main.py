import os
import time
import random
import requests
from datetime import datetime

# Configuración desde variables de entorno
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
INTERVAL = int(os.getenv("SIMULATION_INTERVAL", "5"))

# Configuración de sensores simulados (Ríos de Bogotá como ejemplo)
SENSORS = [
    {"name": "Sensor Puente Aranda", "river": "Río Bogotá", "base_level": 1.5, "sensor_id": None},
    {"name": "Sensor La Calera", "river": "Quebrada La Vieja", "base_level": 1.2, "sensor_id": None},
    {"name": "Sensor Bosa", "river": "Río Fucha", "base_level": 1.8, "sensor_id": None},
    {"name": "Sensor Usme", "river": "Quebrada San Cristóbal", "base_level": 1.0, "sensor_id": None},
]

def wait_for_backend():
    """Espera a que el backend esté listo antes de continuar."""
    print("📡 Esperando a que el backend esté disponible...")
    max_retries = 15
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✅ ¡Backend listo! Iniciando registro de sensores.")
                return True
        except requests.exceptions.RequestException:
            print(f"⏳ Backend no disponible. Reintentando en 3s... ({attempt + 1}/{max_retries})")
            time.sleep(3)
    
    print("❌ No se pudo conectar al backend después de varios intentos.")
    return False

def register_sensors():
    """Registra los sensores en la API y guarda sus IDs."""
    for sensor in SENSORS:
        payload = {
            "name": sensor["name"],
            "river_name": sensor["river"],
            "location": {"lat": 4.6097 + random.uniform(-0.1, 0.1), "lng": -74.0817 + random.uniform(-0.1, 0.1)},
            "installed_date": datetime.utcnow().isoformat()
        }
        try:
            response = requests.post(f"{BACKEND_URL}/sensors/", json=payload)
            if response.status_code == 201:
                sensor["sensor_id"] = response.json()["_id"]
                print(f"  ✅ Registrado: {sensor['name']} (ID: {sensor['sensor_id'][:8]}...)")
            else:
                print(f"  ⚠️ Error registrando {sensor['name']}: {response.text}")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Error de conexión al registrar {sensor['name']}")

def simulate_readings():
    """Envía lecturas de nivel de agua periódicamente."""
    print(f"\n🌊 Iniciando simulación de lecturas cada {INTERVAL} segundos...")
    print("Presiona Ctrl+C en la terminal principal para detener todo.\n")
    
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
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                response = requests.post(f"{BACKEND_URL}/readings/", json=payload)
                if response.status_code == 201:
                    data = response.json()
                    risk = data["risk_level"].upper()
                    emoji = "🟢" if risk == "NORMAL" else "🟡" if risk == "ALERTA" else "🔴"
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {emoji} {sensor['river']} ({sensor['name']}): {water_level}m - Riesgo: {risk}")
            except requests.exceptions.ConnectionError:
                print("  ⚠️ Perdida temporal de conexión con el backend. Se reanudará automáticamente.")
                
        time.sleep(INTERVAL)

if __name__ == "__main__":
    if wait_for_backend():
        register_sensors()
        simulate_readings()
    else:
        exit(1)