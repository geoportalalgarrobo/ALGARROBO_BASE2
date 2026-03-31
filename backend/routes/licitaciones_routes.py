"""
Blueprint: Licitaciones
Rutas: /licitaciones/*, /api/licitaciones/*
"""
import os
import time
import psycopg2.extras
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from core.config import logger, DOCS_FOLDER
from core.database import get_db_connection, release_db_connection
from utils.decorators import session_required
from utils.audit_logger import log_auditoria, allowed_file

licitaciones_bp = Blueprint('licitaciones', __name__)


@licitaciones_bp.route("/licitaciones/pasos", methods=["POST"])
@session_required
def create_licitacion_paso_maestro(current_user_id):
    conn = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(orden), 0) FROM licitacion_pasos_maestro")
            next_orden = cur.fetchone()[0] + 1
            cur.execute("""
                INSERT INTO licitacion_pasos_maestro (orden, nombre, descripcion, documento_requerido)
                VALUES (%s, %s, %s, %s) RETURNING id_paso
            """, (next_orden, data.get("nombre"), data.get("descripcion"), data.get("documento_requerido")))
            new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Paso maestro creado", "id": new_id}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error create_licitacion_paso_maestro: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/pasos", methods=["GET"])
@session_required
def get_licitacion_pasos_maestro(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM licitacion_pasos_maestro ORDER BY orden")
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_licitacion_pasos_maestro: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones", methods=["GET"])
@session_required
def get_licitaciones(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT l.*, p.nombre as proyecto_nombre,
                       (SELECT count(*) FROM licitacion_workflow WHERE licitacion_id = l.id AND estado = 'Completado') as pasos_completados
                FROM licitaciones l
                JOIN proyectos p ON p.id = l.proyecto_id
                ORDER BY l.fecha_actualizacion DESC
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_licitaciones: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/pasos/<int:paso_id>", methods=["PUT"])
@session_required
def update_licitacion_paso_maestro(current_user_id, paso_id):
    conn = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE licitacion_pasos_maestro 
                SET nombre = %s, descripcion = %s, documento_requerido = %s, activo = %s
                WHERE id_paso = %s
            """, (data.get("nombre"), data.get("descripcion"), data.get("documento_requerido"),
                  data.get("activo", True), paso_id))
            log_auditoria(current_user_id, "update_paso_maestro", f"Actualizó paso maestro {paso_id}")
        conn.commit()
        return jsonify({"message": "Paso maestro actualizado"}), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error update_paso_maestro: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones", methods=["POST"])
@session_required
def create_licitacion(current_user_id):
    conn = None
    try:
        data = request.get_json()
        required = ["proyecto_id", "nombre_licitacion"]
        if not data or not all(k in data for k in required):
            return jsonify({"message": "Faltan datos requeridos"}), 400

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nombre_licitacion FROM licitaciones 
                WHERE proyecto_id = %s AND COALESCE(estado_licitacion, 'Abierta') = 'Abierta'
            """, (data["proyecto_id"],))
            existing = cur.fetchone()
            if existing:
                return jsonify({
                    "message": f"El proyecto ya tiene una licitación abierta (ID: {existing[0]} - {existing[1]})."
                }), 409

            monto = data.get("monto_estimado")
            if monto == "" or monto is None:
                monto = None

            cur.execute("""
                INSERT INTO licitaciones (proyecto_id, nombre_licitacion, id_mercado_publico, monto_estimado, usuario_creador, estado_actual_paso, estado_licitacion)
                VALUES (%s, %s, %s, %s, %s, 1, 'Abierta') RETURNING id
            """, (data["proyecto_id"], data["nombre_licitacion"], data.get("id_mercado_publico"), monto, current_user_id))
            lic_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO licitacion_workflow (licitacion_id, paso_id, estado)
                SELECT %s, id_paso, 'Pendiente'
                FROM licitacion_pasos_maestro ORDER BY orden
            """, (lic_id,))

            log_auditoria(current_user_id, "crear_licitacion",
                         f"Inició licitación {lic_id} para proyecto {data['proyecto_id']}")

        conn.commit()
        return jsonify({"message": "Licitación iniciada", "id": lic_id}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error create_licitacion: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/<int:lid>", methods=["GET"])
@session_required
def get_licitacion_detalle(current_user_id, lid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT l.*, p.nombre as proyecto_nombre 
                FROM licitaciones l
                JOIN proyectos p ON p.id = l.proyecto_id
                WHERE l.id = %s
            """, (lid,))
            lic = cur.fetchone()
            if not lic:
                return jsonify({"message": "No encontrada"}), 404

            cur.execute("""
                SELECT w.id, w.licitacion_id, w.paso_id, w.estado,
                       w.fecha_planificada::text as fecha_planificada,
                       w.fecha_real::date::text as fecha_real,
                       w.observaciones, w.usuario_id, w.actualizado_en,
                       m.nombre as paso_nombre, m.orden as paso_orden
                FROM licitacion_workflow w
                JOIN licitacion_pasos_maestro m ON m.id_paso = w.paso_id
                WHERE w.licitacion_id = %s ORDER BY m.orden
            """, (lid,))
            lic["workflow"] = cur.fetchall()

            cur.execute("""
                SELECT d.*, u.nombre as usuario_nombre
                FROM licitaciones_documentos d
                LEFT JOIN users u ON u.user_id = d.usuario_subida
                WHERE d.workflow_id IN (SELECT id FROM licitacion_workflow WHERE licitacion_id = %s)
            """, (lid,))
            docs = cur.fetchall()

            for step in lic["workflow"]:
                step["documentos"] = [d for d in docs if d["workflow_id"] == step["id"]]

        return jsonify(lic)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_licitacion_detalle: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/workflow/<int:wid>", methods=["PUT"])
@session_required
def update_licitacion_workflow(current_user_id, wid):
    conn = None
    try:
        data = request.get_json()
        fields = []
        vals = []
        allowed = ["estado", "fecha_planificada", "fecha_real", "observaciones"]
        for k in allowed:
            if k in data:
                val = data[k]
                if val == "":
                    val = None
                if k == "fecha_real" and val is not None:
                    fields.append(f"{k} = %s::date")
                else:
                    fields.append(f"{k} = %s")
                vals.append(val)

        if not fields:
            return jsonify({"message": "Sin datos"}), 400

        vals.append(current_user_id)
        vals.append(wid)
        sql = f"UPDATE licitacion_workflow SET {', '.join(fields)}, usuario_id = %s, actualizado_en = NOW() WHERE id = %s"

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, tuple(vals))
            cur.execute("UPDATE licitaciones SET fecha_actualizacion = NOW() WHERE id = (SELECT licitacion_id FROM licitacion_workflow WHERE id = %s)", (wid,))
        conn.commit()
        return jsonify({"message": "Paso actualizado"})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error update_licitacion_workflow: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/documentos", methods=["POST"])
@session_required
def upload_licitacion_doc(current_user_id):
    conn = None
    try:
        workflow_id = request.form.get("workflow_id")
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion", "")
        if 'archivo' not in request.files:
            return jsonify({"message": "Sin archivo"}), 400
        f = request.files['archivo']
        if f.filename == '':
            return jsonify({"message": "Nombre vacío"}), 400
        if f and allowed_file(f.filename):
            ts = int(time.time())
            ext = f.filename.rsplit('.', 1)[1].lower()
            fname = secure_filename(f"lic_{workflow_id}_{ts}.{ext}")
            target_dir = os.path.join(DOCS_FOLDER, "licitaciones")
            os.makedirs(target_dir, exist_ok=True)
            fpath = os.path.join(target_dir, fname)
            f.save(fpath)
            url = f"/api/licitaciones/docs/{fname}"
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO licitaciones_documentos 
                    (workflow_id, nombre, descripcion, url, archivo_nombre, archivo_extension, archivo_size, usuario_subida)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (workflow_id, nombre, descripcion, url, f.filename, ext, os.path.getsize(fpath), current_user_id))
            conn.commit()
            return jsonify({"message": "Documento subido", "url": url})
        return jsonify({"message": "Tipo de archivo no permitido"}), 400
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error upload_licitacion_doc: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/api/licitaciones/docs/<filename>")
@session_required
def serve_licitacion_doc(current_user_id, filename):
    target_dir = os.path.join(DOCS_FOLDER, "licitaciones")
    return send_from_directory(target_dir, filename)


@licitaciones_bp.route("/licitaciones/biblioteca", methods=["POST"])
@session_required
def upload_biblioteca_doc(current_user_id):
    conn = None
    try:
        nombre = request.form.get("nombre")
        tipo = request.form.get("tipo", "General")
        descripcion = request.form.get("descripcion", "")
        if 'archivo' not in request.files:
            return jsonify({"message": "Sin archivo"}), 400
        f = request.files['archivo']
        if f.filename == '':
            return jsonify({"message": "Nombre vacío"}), 400
        if f and allowed_file(f.filename):
            ts = int(time.time())
            ext = f.filename.rsplit('.', 1)[1].lower()
            fname = secure_filename(f"lib_{ts}_{f.filename}")
            target_dir = os.path.join(DOCS_FOLDER, "licitaciones", "biblioteca")
            os.makedirs(target_dir, exist_ok=True)
            fpath = os.path.join(target_dir, fname)
            f.save(fpath)
            url = f"/api/licitaciones/lib/{fname}"
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO licitaciones_biblioteca 
                    (nombre, tipo, descripcion, url, archivo_nombre, archivo_extension, archivo_size, usuario_subida)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (nombre, tipo, descripcion, url, f.filename, ext, os.path.getsize(fpath), current_user_id))
            conn.commit()
            return jsonify({"message": "Documento añadido a biblioteca", "url": url})
        return jsonify({"message": "Tipo de archivo no permitido"}), 400
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error upload_biblioteca_doc: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/biblioteca", methods=["GET"])
@session_required
def get_biblioteca_docs(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM licitaciones_biblioteca ORDER BY fecha_subida DESC")
            return jsonify(cur.fetchall())
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_biblioteca_docs: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/<int:lid>/cerrar", methods=["PUT"])
@session_required
def cerrar_licitacion(current_user_id, lid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE licitaciones 
                SET estado_licitacion = 'Cerrada', fecha_actualizacion = NOW()
                WHERE id = %s AND COALESCE(estado_licitacion, 'Abierta') = 'Abierta'
            """, (lid,))
            if cur.rowcount == 0:
                return jsonify({"message": "Licitación no encontrada o ya cerrada"}), 404
            log_auditoria(current_user_id, "cerrar_licitacion", f"Cerró licitación {lid}")
        conn.commit()
        return jsonify({"message": "Licitación cerrada exitosamente"})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error cerrar_licitacion: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/<int:lid>/reabrir", methods=["PUT"])
@session_required
def reabrir_licitacion(current_user_id, lid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT proyecto_id FROM licitaciones WHERE id = %s", (lid,))
            row = cur.fetchone()
            if not row:
                return jsonify({"message": "Licitación no encontrada"}), 404

            proyecto_id = row[0]
            cur.execute("""
                SELECT id FROM licitaciones 
                WHERE proyecto_id = %s AND COALESCE(estado_licitacion, 'Abierta') = 'Abierta' AND id != %s
            """, (proyecto_id, lid))
            if cur.fetchone():
                return jsonify({"message": "Ya existe otra licitación abierta para este proyecto."}), 409

            cur.execute("""
                UPDATE licitaciones 
                SET estado_licitacion = 'Abierta', fecha_actualizacion = NOW()
                WHERE id = %s AND estado_licitacion = 'Cerrada'
            """, (lid,))
            if cur.rowcount == 0:
                return jsonify({"message": "La licitación no está cerrada o no existe"}), 400

            log_auditoria(current_user_id, "reabrir_licitacion", f"Reabrió licitación {lid}")
        conn.commit()
        return jsonify({"message": "Licitación reabierta exitosamente"})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error reabrir_licitacion: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/licitaciones/calendario", methods=["GET"])
@session_required
def get_licitaciones_calendario(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT w.id as workflow_id, w.fecha_planificada::text, w.fecha_real::date::text, w.estado,
                    l.id as licitacion_id, l.nombre_licitacion, l.id_mercado_publico,
                    COALESCE(l.estado_licitacion, 'Abierta') as estado_licitacion,
                    p.nombre as proyecto_nombre, m.nombre as paso_nombre, m.orden as paso_orden
                FROM licitacion_workflow w
                JOIN licitaciones l ON l.id = w.licitacion_id
                JOIN proyectos p ON p.id = l.proyecto_id
                JOIN licitacion_pasos_maestro m ON m.id_paso = w.paso_id
                WHERE (w.fecha_planificada IS NOT NULL OR w.fecha_real IS NOT NULL)
                ORDER BY COALESCE(w.fecha_real, w.fecha_planificada)
            """)
            return jsonify(cur.fetchall())
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_licitaciones_calendario: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@licitaciones_bp.route("/api/licitaciones/lib/<filename>")
@session_required
def serve_biblioteca_doc(current_user_id, filename):
    target_dir = os.path.join(DOCS_FOLDER, "licitaciones", "biblioteca")
    return send_from_directory(target_dir, filename)
