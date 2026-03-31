"""
Blueprint: Gestión de Usuarios, Roles y Divisiones
Rutas: /users/*, /roles, /divisiones/*
"""
import traceback
import bcrypt
import psycopg2.extras
from flask import Blueprint, request, jsonify

from core.config import logger
from core.database import get_db_connection, release_db_connection
from utils.decorators import session_required, admin_required
from utils.audit_logger import log_auditoria

users_bp = Blueprint('users', __name__)


# ─── USERS ─────────────────────────────────────────────────────

@users_bp.route("/users", methods=["GET"])
@session_required
def get_users(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT u.user_id, u.email, u.nombre, u.nivel_acceso,
                       d.nombre AS division, d.division_id,
                       u.activo
                FROM users u
                LEFT JOIN divisiones d ON u.division_id = d.division_id
                ORDER BY u.nombre
            """)
            rows = cur.fetchall()
            for r in rows:
                r["division_nombre"] = r["division"]
        return jsonify(rows)
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error en get_users: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@users_bp.route("/users", methods=["POST"])
@admin_required
def create_user(current_user_id):
    conn = None
    try:
        data = request.get_json()
        required = ["email", "password", "nombre", "nivel_acceso"]
        if not data or not all(k in data for k in required):
            return jsonify({"message": "Datos incompletos"}), 400

        division_id = data.get("division_id")
        hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
        activo = data.get("es_activo", True)

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (email, password_hash, nombre, nivel_acceso, division_id, activo)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """, (data["email"], hashed, data["nombre"], data["nivel_acceso"], division_id, activo))
            new_id = cur.fetchone()[0]
        conn.commit()

        log_auditoria(current_user_id, "create_user", f"Creó user_id={new_id}")
        return jsonify({"message": "Usuario creado", "user_id": new_id}), 201
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error en create_user: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@users_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(current_user_id, user_id):
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Sin datos"}), 400

        fields = []
        values = []
        allowed = {"nombre", "email", "nivel_acceso", "division_id", "activo", "password"}

        for k, v in data.items():
            # Ignorar valores vacíos para evitar sobrescritura muda
            if v == "" or v is None:
                continue
            if k == "es_activo":
                fields.append("activo = %s")
                values.append(v)
                continue
            if k not in allowed:
                continue
            if k == "password":
                hashed = bcrypt.hashpw(v.encode(), bcrypt.gensalt()).decode()
                fields.append("password_hash = %s")
                values.append(hashed)
            else:
                fields.append(f"{k} = %s")
                values.append(v)

        if not fields:
            return jsonify({"message": "No hay campos válidos para actualizar"}), 400

        values.append(user_id)
        sql = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s"

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor() as cur:
            cur.execute(sql, tuple(values))
        conn.commit()

        log_auditoria(current_user_id, "update_user", f"Actualizó user_id={user_id}")
        return jsonify({"message": "Usuario actualizado"})
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error en update_user: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(current_user_id, user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id = %s RETURNING user_id", (user_id,))
            deleted = cur.fetchone()
        conn.commit()

        if not deleted:
            return jsonify({"message": "Usuario no encontrado"}), 404

        log_auditoria(current_user_id, "delete_user", f"Borró user_id={user_id}")
        return jsonify({"message": "Usuario eliminado"})
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error en delete_user: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@users_bp.route("/users/<int:user_id>", methods=["GET"])
@session_required
def get_user(current_user_id, user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    u.user_id, u.email, u.nombre, u.nivel_acceso,
                    u.activo, u.division_id,
                    d.nombre AS division
                FROM users u
                LEFT JOIN divisiones d ON d.division_id = u.division_id
                WHERE u.user_id = %s
            """, (user_id,))
            user = cur.fetchone()

        if not user:
            return jsonify({"message": "Usuario no encontrado"}), 404
        return jsonify(user)
    finally:
        if conn:
            release_db_connection(conn)


@users_bp.route("/users/<int:user_id>/activar", methods=["PUT"])
@admin_required
def activar_usuario(current_user_id, user_id):
    conn = None
    try:
        data = request.get_json()
        activo = data.get("activo")

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET activo = %s WHERE user_id = %s
            """, (activo, user_id))
        conn.commit()

        log_auditoria(current_user_id, "activar_usuario", f"Usuario {user_id} activo={activo}")
        return jsonify({"message": "Estado actualizado"})
    finally:
        if conn:
            release_db_connection(conn)


@users_bp.route("/users/<int:user_id>/reset-password", methods=["PUT"])
@admin_required
def reset_password(current_user_id, user_id):
    conn = None
    try:
        data = request.get_json()
        new_password = data.get("password")
        if not new_password:
            return jsonify({"message": "Password requerido"}), 400

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET password_hash = %s WHERE user_id = %s
            """, (hashed, user_id))
        conn.commit()

        log_auditoria(current_user_id, "reset_password", f"Reseteó password usuario {user_id}")
        return jsonify({"message": "Contraseña actualizada"})
    finally:
        if conn:
            release_db_connection(conn)


# ─── ROLES ─────────────────────────────────────────────────────

@users_bp.route("/roles", methods=["GET"])
@session_required
def get_roles(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT role_id, nombre FROM roles")
            roles = cur.fetchall()
        return jsonify(roles)
    finally:
        if conn:
            release_db_connection(conn)


@users_bp.route("/users/<int:user_id>/roles", methods=["PUT"])
@admin_required
def set_user_roles(current_user_id, user_id):
    conn = None
    try:
        data = request.get_json()
        roles = data.get("roles", [])

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
            for role_id in roles:
                cur.execute("""
                    INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)
                """, (user_id, role_id))
        conn.commit()

        log_auditoria(current_user_id, "set_roles", f"Actualizó roles usuario {user_id}")
        return jsonify({"message": "Roles actualizados"})
    finally:
        if conn:
            release_db_connection(conn)


# ─── DIVISIONES ────────────────────────────────────────────────

@users_bp.route("/divisiones", methods=["GET"])
@session_required
def get_divisiones(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT division_id, nombre FROM divisiones")
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error en get_divisiones: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@users_bp.route("/divisiones", methods=["POST"])
@admin_required
def create_division(current_user_id):
    conn = None
    try:
        data = request.get_json()
        if not data or "nombre" not in data:
            return jsonify({"message": "Nombre requerido"}), 400
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO divisiones (nombre) VALUES (%s) RETURNING division_id",
                (data["nombre"],)
            )
            new_id = cur.fetchone()[0]
        conn.commit()

        log_auditoria(current_user_id, "create_division", f"Creó division_id={new_id}")
        return jsonify({"division_id": new_id}), 201
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error en create_division: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)
