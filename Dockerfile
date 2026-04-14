# Usar Python 3.10 slim como imagen base
FROM python:3.10-slim

# Establecer directorio de trabajo en /app
WORKDIR /app

# Instalar dependencias del sistema requeridas
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Crear el directorio /data que será montado por el volumen de Railway
RUN mkdir -p /data

# Copiar los requerimientos que ahora están en backend/
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el backend a la estructura del contenedor
COPY backend/ ./backend/

# Posicionarnos directamente en backend para un inicio limpio y en contexto
WORKDIR /app/backend

# Comando de inicio usando gunicorn (evaluará automáticamente la variable PORT)
CMD gunicorn app_railway:app --bind 0.0.0.0:${PORT:-8000} --workers 4 --threads 2 --timeout 120
