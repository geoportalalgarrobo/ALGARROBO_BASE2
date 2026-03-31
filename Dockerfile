# 🚀 Railway Master Dockerfile (Backend Modular Optimized)
# ---------------------------------------------------
# Optimizado para:
# - Carga ultra-rápida (Multi-stage build)
# - Persistencia en volumen /data
# - Despliegue del backend únicamente

# ETAPA 1: Builder (Compilación de librerías pesadas)
FROM python:3.11-slim as builder
WORKDIR /build

# Herramientas de compilación esenciales
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalación de requerimientos
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ETAPA 2: Runtime (Imagen final liviana)
FROM python:3.11-slim
WORKDIR /app

# Dependencias de ejecución esenciales
# - antiword y tesseract para extracción de documentos
# - libpq5 para PostgreSQL
RUN apt-get update && apt-get install -y \
    antiword \
    tesseract-ocr \
    tesseract-ocr-spa \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiamos paquetes instalados del builder (ahorra tiempo masivo)
COPY --from=builder /install /usr/local

# Copiamos TODO el backend
COPY backend/ .

# Variables de entorno runtime
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Definimos el volumen /data como base para reportes
ENV AUDIT_OUT_DIR=/data/auditoria_reportes

# Aseguramos que existan las carpetas base (si no están en volumen)
RUN mkdir -p docs fotos_reportes auditoria_reportes

# Exponemos el puerto (aunque Railway lo inyecta dinámicamente)
EXPOSE 8000

# Inicio del servidor con Gunicorn (Optimizado para Railway)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --threads 4 app_railway:app"]
