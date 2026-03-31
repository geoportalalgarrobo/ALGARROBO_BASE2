"""
═══════════════════════════════════════════════════════════════════
 API Municipal – Entrypoint Modular (app_new.py)
 
 Reemplaza el monolito app21.py (~5700 líneas) por una arquitectura
 modular con Flask Blueprints.
 
 Estructura:
   core/config.py      → Variables de entorno, logging, constantes
   core/database.py    → Pool de conexiones PostgreSQL
   utils/auth_utils.py → JWT: create/validate/remove session
   utils/decorators.py → @session_required, @admin_required
   utils/audit_logger.py → log_control, log_auditoria
   routes/auth_routes.py        → /auth/*
   routes/users_routes.py       → /users/*, /roles, /divisiones/*
   routes/proyectos_routes.py   → /proyectos/*, catálogos CRUD
   routes/licitaciones_routes.py → /licitaciones/*
   routes/documentos_routes.py  → /documentos/*, /geomapas/*, /hitos/*,
                                   /observaciones/*, /proximos_pasos/*, /mapas/*
   routes/calendario_routes.py  → /calendario_eventos/*, /hitoscalendario/*,
                                   /auditoria (legacy)
   routes/mobile_routes.py      → /api/mobile/*, /api/admin/*, /api/volume/*
   routes/control_routes.py     → /control/*
   routes/auditoria_routes.py   → /auditoria/* (integral)
═══════════════════════════════════════════════════════════════════
"""
import os
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ─── Módulos Core ──────────────────────────────────────────────
from core.config import (
    logger, APP_HOST, APP_PORT, DEBUG,
    ALLOWED_ORIGINS, DOCS_FOLDER
)
from core.database import (
    init_connection_pool, get_db_connection,
    release_db_connection, cleanup_pool, connection_pool
)

# ─── Blueprints ────────────────────────────────────────────────
from routes.auth_routes import auth_bp
from routes.users_routes import users_bp
from routes.proyectos_routes import proyectos_bp
from routes.licitaciones_routes import licitaciones_bp
from routes.documentos_routes import documentos_bp
from routes.calendario_routes import calendario_bp
from routes.mobile_routes import mobile_bp
from routes.control_routes import control_bp
from routes.auditoria_routes import auditoria_bp


# ═══════════════════════════════════════════════════════════════
# CREAR APP
# ═══════════════════════════════════════════════════════════════
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1GB para migración ZIP

# CORS restrictivo
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)


# ─── Middleware ─────────────────────────────────────────────────
@app.before_request
def log_request_info():
    if request.path.startswith('/api') or request.path.startswith('/auth'):
        logger.info(f"REQUEST {request.method} {request.path}")


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Internal server error: {e}")
    logger.error(traceback.format_exc())
    code = getattr(e, 'code', 500)
    # SEGURIDAD [H-10]: No exponer str(e) al cliente
    response = jsonify({
        "error": "Se produjo un error interno. Revise los logs del servidor.",
        "code": code
    })
    response.status_code = code
    return response


# ─── Registrar Blueprints (9 módulos) ─────────────────────────
app.register_blueprint(auth_bp)          # /auth/*
app.register_blueprint(users_bp)         # /users/*, /roles, /divisiones/*
app.register_blueprint(proyectos_bp)     # /proyectos/*, catálogos
app.register_blueprint(licitaciones_bp)  # /licitaciones/*
app.register_blueprint(documentos_bp)    # /documentos/*, /geomapas/*, /hitos/*, /observaciones/*
app.register_blueprint(calendario_bp)    # /calendario_eventos/*, /hitoscalendario/*
app.register_blueprint(mobile_bp)        # /api/mobile/*, /api/admin/*, /api/volume/*
app.register_blueprint(control_bp)       # /control/*
app.register_blueprint(auditoria_bp)     # /auditoria/*


# ─── Rutas base ────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({"message": "API Municipal funcionando (Modular + Blueprints)"})


@app.route("/docs/<path:filename>")
def serve_docs(filename):
    """Servir archivos estáticos de documentos de proyectos."""
    return send_from_directory(DOCS_FOLDER, filename)


@app.route("/health")
def health_check():
    """Endpoint para verificar el estado de la aplicación y la conexión a la BD."""
    from core.database import connection_pool as pool
    try:
        pool_status = {
            "initialized": pool is not None and not pool.closed,
            "min_connections": pool.minconn if pool else None,
            "max_connections": pool.maxconn if pool else None,
        }

        db_status = "disconnected"
        try:
            conn = get_db_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                db_status = "connected"
                release_db_connection(conn)
        except Exception as e:
            logger.error(f"Error en health check de BD: {e}")
            db_status = "error"

        if db_status == "connected" and pool_status["initialized"]:
            status_code = 200
            status = "healthy"
        else:
            status_code = 503
            status = "unhealthy"

        return jsonify({
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "database": {"status": db_status},
            "connection_pool": pool_status,
            "auth_type": "JWT (Stateless)",
            "version": "3.0.0-modular",
            "architecture": "Flask Blueprints",
            "blueprints": 9
        }), status_code
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat()
        }), 503


@app.teardown_appcontext
def close_connection(exception=None):
    pass  # Conexiones gestionadas manualmente con release_db_connection


# ═══════════════════════════════════════════════════════════════
# INICIALIZACIÓN
# ═══════════════════════════════════════════════════════════════
logger.info("Backend Municipal (Modular) iniciando...")
logger.info("Registrados 9 Blueprints")
if not init_connection_pool():
    logger.error("No se pudo inicializar el pool de conexiones al inicio")


# ═══════════════════════════════════════════════════════════════
# START
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    try:
        cert_path = os.path.abspath("fullchain.pem")
        key_path = os.path.abspath("private.key")
        logger.info(f"Iniciando servidor en https://{APP_HOST}:{APP_PORT}")
        logger.info("Endpoint de health check disponible en /health")
        logger.info("Migración completa: 0 rutas legacy restantes")
        app.run(host=APP_HOST, port=APP_PORT, debug=DEBUG,
                ssl_context=(cert_path, key_path))
    finally:
        cleanup_pool()
