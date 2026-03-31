"""
Decoradores de autenticación y autorización para rutas Flask.
"""
from functools import wraps
from flask import request, jsonify
from utils.auth_utils import validate_session
from core.database import get_db_connection, release_db_connection
from core.config import logger


def session_required(f):
    """Decorador que requiere un token JWT válido."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({}), 200

        auth = request.headers.get("Authorization", "")
        token = None
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
        elif request.args.get("token"):
            token = request.args.get("token")
        elif auth:
            token = auth.strip()

        if not token:
            return jsonify({"message": "Token requerido"}), 401

        user_id = validate_session(token)
        if user_id is None:
            return jsonify({"message": "Sesión inválida o expirada"}), 401

        return f(user_id, *args, **kwargs)
    return decorated


def admin_required(f):
    """
    Decorador que requiere autenticación Y nivel_acceso >= 10.
    SEGURIDAD [H-05]: Verificación de permisos de admin a nivel de BD.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({}), 200

        auth = request.headers.get("Authorization", "")
        token = None
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
        elif request.args.get("token"):
            token = request.args.get("token")
        elif auth:
            token = auth.strip()

        if not token:
            return jsonify({"message": "Token requerido"}), 401

        user_id = validate_session(token)
        if user_id is None:
            return jsonify({"message": "Sesión inválida o expirada"}), 401

        # Verificar nivel de acceso en BD
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT nivel_acceso FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = cur.fetchone()
                if not row or row[0] < 10:
                    return jsonify({
                        "message": "No autorizado. Se requiere nivel de acceso administrativo."
                    }), 403
        finally:
            release_db_connection(conn)

        return f(user_id, *args, **kwargs)
    return decorated
