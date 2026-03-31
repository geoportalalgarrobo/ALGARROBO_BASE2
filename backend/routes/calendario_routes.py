"""
Blueprint: Calendario, HitosCalendario y Auditoría Legacy
Rutas: /calendario_eventos/*, /hitoscalendario/*, /auditoria,
       /calendario_eventos_detalle
"""
import psycopg2.extras
from flask import Blueprint, request, jsonify

from core.config import logger
from core.database import get_db_connection, release_db_connection
from utils.decorators import session_required
from utils.audit_logger import log_auditoria

calendario_bp = Blueprint('calendario', __name__)


# ─── CALENDARIO EVENTOS ───────────────────────────────────────

@calendario_bp.route("/calendario_eventos", methods=["POST"])
@session_required
def create_calendario_evento(current_user_id):
    conn = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO calendario_eventos (
                    titulo, descripcion, fecha_inicio, fecha_termino,
                    todo_el_dia, categoria_calendario, origen_tipo,
                    origen_id, ubicacion, creado_por
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (
                data["titulo"], data.get("descripcion"),
                data["fecha_inicio"], data.get("fecha_termino"),
                data.get("todo_el_dia", True), data.get("categoria_calendario"),
                data.get("origen_tipo"), data.get("origen_id"),
                data.get("ubicacion"), current_user_id
            ))
            event_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"id": event_id}), 201
    finally:
        if conn: release_db_connection(conn)


@calendario_bp.route("/calendario_eventos", methods=["GET"])
@session_required
def get_calendario_eventos(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT e.*, hc.nombre AS categoria_nombre
                FROM calendario_eventos e
                LEFT JOIN hitoscalendario hc ON hc.id = e.categoria_calendario
                WHERE e.activo = TRUE ORDER BY e.fecha_inicio
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    finally:
        if conn: release_db_connection(conn)


@calendario_bp.route("/calendario_eventos/<int:evento_id>", methods=["PUT"])
@session_required
def update_calendario_evento(current_user_id, evento_id):
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Sin datos"}), 400

        allowed = {
            "titulo", "descripcion", "fecha_inicio", "fecha_termino",
            "todo_el_dia", "origen_tipo", "origen_id", "ubicacion", "activo"
        }
        fields, values = [], []
        for k, v in data.items():
            if k in allowed:
                fields.append(f"{k} = %s")
                values.append(v)
        if not fields:
            return jsonify({"message": "No hay campos válidos"}), 400

        values.append(evento_id)
        sql = f"UPDATE calendario_eventos SET {', '.join(fields)} WHERE id = %s"

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, values)
        conn.commit()

        log_auditoria(current_user_id, "update_evento",
                      f"Actualizó evento calendario id={evento_id}")
        return jsonify({"message": "Evento actualizado"})
    finally:
        if conn: release_db_connection(conn)


@calendario_bp.route("/calendario_eventos/<int:evento_id>", methods=["DELETE"])
@session_required
def delete_calendario_evento(current_user_id, evento_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE calendario_eventos SET activo = FALSE
                WHERE id = %s AND activo = TRUE
            """, (evento_id,))
            if cur.rowcount == 0:
                return jsonify({"message": "Evento no encontrado"}), 404
        conn.commit()

        log_auditoria(current_user_id, "delete_evento",
                      f"Desactivó evento calendario id={evento_id}")
        return jsonify({"message": "Evento desactivado"})
    finally:
        if conn: release_db_connection(conn)


# ─── HITOSCALENDARIO ──────────────────────────────────────────

@calendario_bp.route("/hitoscalendario", methods=["GET"])
@session_required
def get_hitoscalendario(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, nombre, is_hito FROM hitoscalendario ORDER BY nombre")
            rows = cur.fetchall()
        return jsonify(rows)
    finally:
        if conn: release_db_connection(conn)


@calendario_bp.route("/hitoscalendario", methods=["POST"])
@session_required
def create_hitoscalendario(current_user_id):
    conn = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hitoscalendario (nombre, is_hito)
                VALUES (%s, %s) RETURNING id
            """, (data["nombre"], data.get("is_hito", True)))
            new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"id": new_id}), 201
    finally:
        if conn: release_db_connection(conn)


@calendario_bp.route("/hitoscalendario/<int:id>", methods=["PUT"])
@session_required
def update_hitoscalendario(current_user_id, id):
    conn = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE hitoscalendario SET nombre = %s, is_hito = %s WHERE id = %s
            """, (data["nombre"], data.get("is_hito", True), id))
        conn.commit()
        return jsonify({"message": "Actualizado"})
    finally:
        if conn: release_db_connection(conn)


@calendario_bp.route("/hitoscalendario/<int:id>", methods=["DELETE"])
@session_required
def delete_hitoscalendario(current_user_id, id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hitoscalendario WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"message": "Eliminado"})
    finally:
        if conn: release_db_connection(conn)


@calendario_bp.route("/calendario_eventos_detalle", methods=["GET"])
@session_required
def get_calendario_eventos_detalle(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM vw_calendario_eventos_full ORDER BY fecha_inicio
            """)
            eventos = cur.fetchall()
        return jsonify(eventos), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error calendario_eventos_detalle: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── AUDITORÍA LEGACY ─────────────────────────────────────────

@calendario_bp.route("/auditoria", methods=["GET"])
@session_required
def get_auditoria(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT a.audit_id, a.user_id, u.nombre AS usuario,
                       a.accion, a.descripcion, a.fecha
                FROM auditoria a
                LEFT JOIN users u ON a.user_id = u.user_id
                LIMIT 1000
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en get_auditoria: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)
