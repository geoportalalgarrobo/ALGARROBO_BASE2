"""
Blueprint: Autenticación (Login / Logout)
Rutas: /auth/*
"""
import bcrypt
import psycopg2.extras
from flask import Blueprint, request, jsonify, make_response

from core.config import logger
from core.database import get_db
from core.limiter import limiter
from utils.auth_utils import create_session, remove_session
from utils.decorators import session_required
from utils.audit_logger import log_auditoria

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    try:
        data = request.get_json()
        if not data or "email" not in data or "password" not in data:
            return jsonify({"message": "Credenciales incompletas"}), 400

        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 1. Obtener usuario + división
                cur.execute("""
                    SELECT
                        u.user_id,
                        u.password_hash,
                        u.nombre,
                        u.nivel_acceso,
                        u.activo,
                        u.division_id,
                        d.nombre AS division_nombre
                    FROM users u
                    LEFT JOIN divisiones d ON d.division_id = u.division_id
                    WHERE u.email = %s
                """, (data["email"],))
                user = cur.fetchone()

                if not user or not user["activo"]:
                    return jsonify({"message": "Credenciales inválidas"}), 401

                # 2. Validar contraseña
                stored_hash = user["password_hash"] or b""
                if isinstance(stored_hash, str):
                    stored_hash = stored_hash.encode()

                if not bcrypt.checkpw(data["password"].encode(), stored_hash):
                    return jsonify({"message": "Credenciales inválidas"}), 401

                # 3. Obtener roles
                cur.execute("""
                    SELECT r.role_id, r.nombre
                    FROM roles r
                    INNER JOIN user_roles ur ON ur.role_id = r.role_id
                    WHERE ur.user_id = %s
                """, (user["user_id"],))
                roles = [
                    {"role_id": row["role_id"], "nombre": row["nombre"]}
                    for row in cur.fetchall()
                ]

                # 4. Actualizar último login
                cur.execute("""
                    UPDATE users SET fecha_ultimo_login = NOW() WHERE user_id = %s
                """, (user["user_id"],))
                conn.commit()

        # 5. Crear token JWT (fuera del bloque de conexión)
        token = create_session(user["user_id"])
        log_auditoria(user["user_id"], "login", f"Inicio de sesión desde {request.remote_addr}")

        # 6. Respuesta
        response = make_response(jsonify({
            "token": token,
            "user": {
                "id": user["user_id"],
                "nombre": user["nombre"],
                "nivel_acceso": user["nivel_acceso"],
                "division": {
                    "division_id": user["division_id"],
                    "nombre": user["division_nombre"]
                },
                "roles": roles
            }
        }))
        response.set_cookie('authToken', token, httponly=True, secure=True, samesite='Strict')
        return response

    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({"message": "Error interno del servidor"}), 500


@auth_bp.route("/logout", methods=["POST"])
@session_required
def logout(current_user_id):
    try:
        auth = request.headers.get("Authorization", "")
        token = auth.split(" ", 1)[1].strip() if auth.startswith("Bearer ") else auth.strip()

        remove_session(token)
        log_auditoria(current_user_id, "logout", f"Cierre de sesión desde {request.remote_addr}")

        return jsonify({"message": "Sesión cerrada"})
    except Exception as e:
        logger.error(f"Error en logout: {e}")
        return jsonify({"message": "Error interno del servidor"}), 500
