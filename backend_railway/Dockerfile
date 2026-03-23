# Backend Railway - Versión Ultra-Liviana
FROM python:3.11-slim

# 1. Instalamos solo dependencias esenciales. 
# Reemplazamos LibreOffice (+500MB) por Antiword (<1MB)
RUN apt-get update && apt-get install -y \
    antiword \
    tesseract-ocr \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Instalamos requerimientos de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copiamos el resto del código
COPY . .

# 4. Variables de entorno básicas
ENV PYTHONUNBUFFERED=1

# 5. Puerto dinámico para Railway
# Railway inyecta la variable $PORT automáticamente
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app21:app"]
