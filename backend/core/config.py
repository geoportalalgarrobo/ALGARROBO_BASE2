"""
Configuración centralizada de la aplicación.
Carga .env, configura logging, CORS y constantes globales.
"""
import os
import logging
from dotenv import load_dotenv

# ─── Cargar .env ───────────────────────────────────────────────
load_dotenv()

# ─── JWT ───────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET:
    raise ValueError(
        "FATAL: JWT_SECRET_KEY no está configurada. "
        "Defina la variable de entorno JWT_SECRET_KEY antes de iniciar."
    )

# ─── Base de Datos ─────────────────────────────────────────────
DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
if not DB_CONNECTION_STRING:
    raise ValueError("No DATABASE_URL set for Flask application")

# ─── Servidor ──────────────────────────────────────────────────
APP_HOST = "186.67.61.251"
APP_PORT = int(os.getenv("PORT", 8000))
# SEGURIDAD [H-06]: Debug OFF por defecto en producción
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("1", "true", "yes")

# ─── CORS ──────────────────────────────────────────────────────
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_raw:
    ALLOWED_ORIGINS = [origin.strip() for origin in allowed_origins_raw.split(",")]
else:
    # SEGURIDAD [H-03]: Sin wildcard – rechazar por defecto si no hay orígenes
    ALLOWED_ORIGINS = [
        "*"
    ]
    logging.getLogger(__name__).warning(
        "ALLOWED_ORIGINS no definida. Usando orígenes localhost por defecto. "
        "Configure ALLOWED_ORIGINS en producción."
    )

# ─── Sesiones ──────────────────────────────────────────────────
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", 24))

# ─── Archivos ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Esto apunta a backend/ ya que config.py está en backend/core/
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BACKEND_DIR)  # subimos de core/ a backend/

DOCS_FOLDER = os.path.join(BACKEND_DIR, "docs")
os.makedirs(DOCS_FOLDER, exist_ok=True)

FOTOS_DIR = os.path.join(BACKEND_DIR, "fotos_reportes")
os.makedirs(FOTOS_DIR, exist_ok=True)

AUDIT_OUT_DIR = os.getenv(
    "AUDIT_OUT_DIR",
    os.path.join(BACKEND_DIR, "auditoria_reportes")
)
if os.path.exists("/data") or os.path.isdir("/data"):
    AUDIT_OUT_DIR = "/data/auditoria_reportes"
os.makedirs(AUDIT_OUT_DIR, exist_ok=True)

FOTOS_OUT_DIR = AUDIT_OUT_DIR.replace("auditoria_reportes", "fotos_reportes")
os.makedirs(FOTOS_OUT_DIR, exist_ok=True)

# ─── Extensiones de archivo permitidas ─────────────────────────
ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx",
    "png", "jpg", "jpeg",
}

# ─── Tablas permitidas para CRUD genérico ──────────────────────
# SEGURIDAD [H-07]: Lista blanca de tablas para evitar SQL injection
ALLOWED_TABLES_READ = frozenset({
    "areas",
    "financiamientos",
    "estados_postulacion",
    "sectores",
    "lineamientos_estrategicos",
    "etapas_proyecto",
    "estados_proyecto",
})

# ─── Logging ───────────────────────────────────────────────────
def setup_logging():
    """Configura logging centralizado."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("municipal_api.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("municipal_api")


logger = setup_logging()
