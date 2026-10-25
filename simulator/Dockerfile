FROM python:3.11-slim

WORKDIR /app

# Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del simulador
COPY . .

# Ejecutar el script principal
CMD ["python", "main.py"]