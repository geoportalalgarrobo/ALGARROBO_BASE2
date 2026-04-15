"""
Blueprint: Documentos, Geomapas, Hitos y Observaciones de Proyectos
Rutas: /proyectos/<pid>/documentos/*, /documentos/*, /geomapas/*,
       /proyectos/<pid>/hitos/*, /hitos/*, /observaciones/*,
       /proyectos/<pid>/observaciones/*, /proyectos/<pid>/proximos_pasos/*,
       /mapas/por-rol/*
"""
import os
import io
import json
import time
import zipfile
import traceback
import psycopg2.extras
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

from core.config import logger, DOCS_FOLDER, ALLOWED_EXTENSIONS
from core.database import get_db_connection, release_db_connection
from utils.decorators import session_required
from utils.audit_logger import log_auditoria, log_control, allowed_file

# Importación diferida de extract para evitar crash si no existe
try:
    from extract import extract_text_from_file
except ImportError:
    def extract_text_from_file(path, ext):
        return ""

documentos_bp = Blueprint('documentos', __name__)


# ─── DOCUMENTOS ────────────────────────────────────────────────

@documentos_bp.route("/proyectos/<int:pid>/documentos", methods=["POST"])
@session_required
def add_doc(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()
        if not data or "nombre_archivo" not in data or "url_archivo" not in data:
            return jsonify({"message": "Datos incompletos"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documentos (proyecto_id, nombre_archivo, url_archivo)
                VALUES (%s, %s, %s) RETURNING doc_id
            """, (pid, data["nombre_archivo"], data["url_archivo"]))
            doc_id = cur.fetchone()[0]
        conn.commit()

        log_auditoria(current_user_id, "add_documento", f"Agregó doc_id={doc_id} al proyecto {pid}")
        return jsonify({"message": "Documento agregado", "doc_id": doc_id}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en add_doc: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/<int:pid>/documentos/upload", methods=["POST"])
@session_required
def upload_documento(current_user_id, pid):
    conn = None
    try:
        if "file" not in request.files:
            return jsonify({"message": "Archivo no enviado"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"message": "Nombre de archivo vacío"}), 400
        if not allowed_file(file.filename):
            return jsonify({"message": "Tipo de archivo no permitido"}), 400

        tipo_documento = request.form.get("tipo_documento")
        descripcion = request.form.get("descripcion")
        filename = secure_filename(file.filename)
        extension = filename.rsplit(".", 1)[1].lower()

        proyecto_dir = os.path.join(DOCS_FOLDER, str(pid))
        os.makedirs(proyecto_dir, exist_ok=True)

        unique_name = f"{int(time.time())}_{filename}"
        file_path = os.path.join(proyecto_dir, unique_name)
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        file_url = f"/api/docs/{pid}/{unique_name}"

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proyectos_documentos (
                    proyecto_id, tipo_documento, nombre, descripcion,
                    url, archivo_nombre, archivo_extension, archivo_size
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING documento_id
            """, (pid, tipo_documento, filename, descripcion,
                  file_url, unique_name, extension, file_size))
            documento_id = cur.fetchone()[0]
            cur.execute("UPDATE proyectos SET fecha_actualizacion = NOW() WHERE id = %s", (pid,))
        conn.commit()

        log_auditoria(current_user_id, "upload_documento",
                      f"Subió documento {documento_id} al proyecto {pid}")
        return jsonify({"message": "Documento subido correctamente",
                        "documento_id": documento_id, "url": file_url}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en upload_documento: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/<int:pid>/documentos", methods=["GET"])
@session_required
def listar_documentos_proyecto(current_user_id, pid):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT documento_id, proyecto_id, tipo_documento, nombre,
                       descripcion, url, archivo_nombre, archivo_extension,
                       archivo_size, fecha_subida
                FROM proyectos_documentos
                WHERE proyecto_id = %s
            """, (pid,))
            documentos = cur.fetchall()
        return jsonify({"proyecto_id": pid, "total": len(documentos), "documentos": documentos})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error listando documentos proyecto {pid}: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/<int:pid>/documentos/descargar", methods=["GET"])
@session_required
def descargar_documentos_proyecto(current_user_id, pid):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT archivo_nombre FROM proyectos_documentos WHERE proyecto_id = %s", (pid,))
            archivos = cur.fetchall()

        if not archivos:
            return jsonify({"message": "El proyecto no tiene documentos"}), 404

        proyecto_dir = os.path.join(DOCS_FOLDER, str(pid))
        if not os.path.exists(proyecto_dir):
            return jsonify({"message": "Carpeta de documentos no encontrada"}), 404

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for a in archivos:
                file_path = os.path.join(proyecto_dir, a["archivo_nombre"])
                if os.path.exists(file_path):
                    zipf.write(file_path, arcname=a["archivo_nombre"])
        zip_buffer.seek(0)

        log_auditoria(current_user_id, "download_documentos",
                      f"Descargó documentos del proyecto {pid}")
        return send_file(zip_buffer, mimetype="application/zip",
                         as_attachment=True, download_name=f"proyecto_{pid}_documentos.zip")
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error descargando documentos proyecto {pid}: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/documentos", methods=["GET"])
@session_required
def get_all_documentos(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT d.documento_id, d.proyecto_id, p.nombre as proyecto_nombre,
                       d.tipo_documento, d.nombre, d.descripcion, d.url,
                       d.archivo_nombre, d.archivo_extension, d.archivo_size, d.fecha_subida
                FROM proyectos_documentos d
                LEFT JOIN proyectos p ON p.id = d.proyecto_id
                ORDER BY d.fecha_subida DESC
            """)
            documentos = cur.fetchall()
        return jsonify(documentos)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error listando todos los documentos: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/documentos/<int:documento_id>", methods=["GET"])
@session_required
def get_documento_metadata(current_user_id, documento_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT documento_id, proyecto_id, tipo_documento, nombre,
                       descripcion, archivo_extension, archivo_size, fecha_subida
                FROM proyectos_documentos WHERE documento_id = %s
            """, (documento_id,))
            doc = cur.fetchone()
        if not doc:
            return jsonify({"message": "Documento no encontrado"}), 404
        return jsonify(doc)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_documento_metadata: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/documentos/<int:documento_id>/view", methods=["GET"])
@session_required
def view_documento(current_user_id, documento_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT proyecto_id, archivo_nombre, archivo_extension, nombre
                FROM proyectos_documentos WHERE documento_id = %s
            """, (documento_id,))
            doc = cur.fetchone()

        if not doc:
            return jsonify({"message": "Documento no encontrado"}), 404

        file_path = os.path.join(DOCS_FOLDER, str(doc["proyecto_id"]), doc["archivo_nombre"])
        if not os.path.exists(file_path):
            return jsonify({"message": "Archivo no existe en disco"}), 404

        mime_map = {
            "pdf": "application/pdf", "png": "image/png",
            "jpg": "image/jpeg", "jpeg": "image/jpeg"
        }
        mimetype = mime_map.get(doc["archivo_extension"].lower(), "application/octet-stream")
        return send_file(file_path, mimetype=mimetype,
                         as_attachment=False, download_name=doc["nombre"])
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error view_documento: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


def get_texto_documentos_proyecto(proyecto_id):
    """Extrae texto de todos los documentos de un proyecto."""
    conn = None
    textos = []
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT archivo_nombre, archivo_extension
                FROM proyectos_documentos WHERE proyecto_id = %s
            """, (proyecto_id,))
            documentos = cur.fetchall()

        proyecto_dir = os.path.join(DOCS_FOLDER, str(proyecto_id))
        for doc in documentos:
            ext = doc["archivo_extension"].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            file_path = os.path.join(proyecto_dir, doc["archivo_nombre"])
            if not os.path.exists(file_path):
                continue
            texto = extract_text_from_file(file_path, ext)
            if texto.strip():
                textos.append(f"\n--- Documento: {doc['archivo_nombre']} ---\n{texto}")
        return "\n".join(textos)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error leyendo documentos proyecto {proyecto_id}: {e}")
        return ""
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/<int:pid>/documentos/texto", methods=["GET"])
@session_required
def obtener_texto_documentos(current_user_id, pid):
    texto = get_texto_documentos_proyecto(pid)
    return jsonify({"proyecto_id": pid, "texto": texto, "chars": len(texto)})


# ─── MAPAS POR ROL ─────────────────────────────────────────────

@documentos_bp.route("/mapas/por-rol/<int:role_id>", methods=["GET"])
@session_required
def get_mapas_by_role(current_user_id, role_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT m.mapa_id, m.nombre, m.descripcion
                FROM mapas m
                INNER JOIN mapas_roles mr ON mr.mapa_id = m.mapa_id
                WHERE mr.role_id = %s
            """, (role_id,))
            mapas = cur.fetchall()
        return jsonify({"role_id": role_id, "mapas": mapas})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en get_mapas_by_role: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── GEOMAPAS ──────────────────────────────────────────────────

@documentos_bp.route("/proyectos/<int:pid>/geomapas", methods=["POST"])
@session_required
def crear_geomapa(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()
        if not data or "geojson" not in data:
            return jsonify({"message": "GeoJSON requerido"}), 400

        nombre = data.get("nombre")
        descripcion = data.get("descripcion")
        geojson = data["geojson"]

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proyectos_geomapas (proyecto_id, nombre, descripcion, geojson)
                VALUES (%s, %s, %s, %s::jsonb) RETURNING geomapa_id
            """, (pid, nombre, descripcion, json.dumps(geojson)))
            geomapa_id = cur.fetchone()[0]
        conn.commit()

        log_auditoria(current_user_id, "crear_geomapa",
                      f"Creó geomapa {geomapa_id} en proyecto {pid}")
        return jsonify({"message": "Geomapa creado correctamente", "geomapa_id": geomapa_id}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error crear_geomapa: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/<int:pid>/geomapas", methods=["GET"])
@session_required
def listar_geomapas_proyecto(current_user_id, pid):
    """SEGURIDAD [H-09]: Agregado @session_required."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT geomapa_id, proyecto_id, nombre, descripcion, fecha_creacion
                FROM proyectos_geomapas WHERE proyecto_id = %s
            """, (pid,))
            geomapas = cur.fetchall()
        return jsonify({"proyecto_id": pid, "total": len(geomapas), "geomapas": geomapas})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error listando geomapas proyecto {pid}: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/geomapas/<int:geomapa_id>", methods=["GET"])
@session_required
def get_geomapa_metadata(current_user_id, geomapa_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT geomapa_id, proyecto_id, nombre, descripcion, fecha_creacion
                FROM proyectos_geomapas WHERE geomapa_id = %s
            """, (geomapa_id,))
            geomapa = cur.fetchone()
        if not geomapa:
            return jsonify({"message": "Geomapa no encontrado"}), 404
        return jsonify(geomapa)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_geomapa_metadata: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/geomapas/<int:geomapa_id>/geojson", methods=["GET"])
@session_required
def view_geomapa_geojson(current_user_id, geomapa_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT geojson FROM proyectos_geomapas WHERE geomapa_id = %s",
                        (geomapa_id,))
            result = cur.fetchone()
        if not result:
            return jsonify({"message": "Geomapa no encontrado"}), 404

        log_auditoria(current_user_id, "view_geomapa", f"Visualizó geomapa {geomapa_id}")
        return jsonify(result["geojson"])
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error view_geomapa_geojson: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── HITOS ─────────────────────────────────────────────────────

@documentos_bp.route("/proyectos/<int:pid>/hitos", methods=["POST"])
@session_required
def create_proyecto_hito(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proyectos_hitos (proyecto_id, fecha, observacion, categoria_hito, creado_por)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (pid, data["fecha"], data.get("observacion"),
                  data.get("categoria_hito"), current_user_id))
            hito_id = cur.fetchone()[0]
            cur.execute("UPDATE proyectos SET fecha_actualizacion = NOW() WHERE id = %s", (pid,))
        conn.commit()
        return jsonify({"id": hito_id}), 201
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/<int:pid>/hitos", methods=["GET"])
@session_required
def get_proyecto_hitos(current_user_id, pid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT h.*, hc.nombre AS categoria_nombre, u.nombre AS nombre_creador
                FROM proyectos_hitos h
                LEFT JOIN hitoscalendario hc ON hc.id = h.categoria_hito
                LEFT JOIN users u ON u.user_id = h.creado_por
                WHERE h.proyecto_id = %s ORDER BY h.fecha
            """, (pid,))
            rows = cur.fetchall()
        return jsonify(rows)
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/hitos/<int:hito_id>", methods=["GET"])
@session_required
def get_hito_metadata(current_user_id, hito_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, proyecto_id, fecha, observacion, creado_por, creado_en
                FROM proyectos_hitos WHERE id = %s
            """, (hito_id,))
            hito = cur.fetchone()
        if not hito:
            return jsonify({"message": "Hito no encontrado"}), 404
        return jsonify(hito)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_hito_metadata: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/hitos/<int:hito_id>/detalle", methods=["GET"])
@session_required
def view_hito_detalle(current_user_id, hito_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT fecha, observacion, creado_por
                FROM proyectos_hitos WHERE id = %s
            """, (hito_id,))
            hito = cur.fetchone()
        if not hito:
            return jsonify({"message": "Hito no encontrado"}), 404

        log_auditoria(current_user_id, "view_hito", f"Visualizó hito {hito_id}")
        return jsonify(hito)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error view_hito_detalle: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── OBSERVACIONES ─────────────────────────────────────────────

@documentos_bp.route("/proyectos/<int:pid>/observaciones", methods=["POST"])
@session_required
def crear_observacion(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()
        if not data or "fecha" not in data:
            return jsonify({"message": "fecha es requerida"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proyectos_observaciones (proyecto_id, fecha, observacion, creado_por)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (pid, data["fecha"], data.get("observacion"), current_user_id))
            observacion_id = cur.fetchone()[0]
        conn.commit()

        log_auditoria(current_user_id, "crear_observacion",
                      f"Creó observación {observacion_id} en proyecto {pid}")
        return jsonify({"message": "Observación creada correctamente",
                        "observacion_id": observacion_id}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error crear_observacion: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/<int:pid>/observaciones", methods=["GET"])
@session_required
def listar_observaciones_proyecto(current_user_id, pid):
    """SEGURIDAD [H-09]: Agregado @session_required."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT o.id, o.proyecto_id, o.fecha, o.observacion,
                       o.creado_por, u.nombre AS nombre_creador, o.creado_en
                FROM proyectos_observaciones o
                LEFT JOIN users u ON u.user_id = o.creado_por
                WHERE o.proyecto_id = %s
            """, (pid,))
            observaciones = cur.fetchall()
        return jsonify({"proyecto_id": pid, "total": len(observaciones),
                        "observaciones": observaciones})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error listando observaciones proyecto {pid}: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/observaciones/<int:observacion_id>", methods=["GET"])
@session_required
def get_observacion_metadata(current_user_id, observacion_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, proyecto_id, fecha, observacion, creado_por, creado_en
                FROM proyectos_observaciones WHERE id = %s
            """, (observacion_id,))
            observacion = cur.fetchone()
        if not observacion:
            return jsonify({"message": "Observación no encontrada"}), 404
        return jsonify(observacion)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error get_observacion_metadata: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/observaciones/<int:observacion_id>/detalle", methods=["GET"])
@session_required
def view_observacion_detalle(current_user_id, observacion_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT fecha, observacion, creado_por
                FROM proyectos_observaciones WHERE id = %s
            """, (observacion_id,))
            observacion = cur.fetchone()
        if not observacion:
            return jsonify({"message": "Observación no encontrada"}), 404

        log_auditoria(current_user_id, "view_observacion",
                      f"Visualizó observación {observacion_id}")
        return jsonify(observacion)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error view_observacion_detalle: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── PRÓXIMOS PASOS ───────────────────────────────────────────

@documentos_bp.route("/proyectos/<int:pid>/proximos_pasos", methods=["GET"])
@session_required
def listar_proximos_pasos(current_user_id, pid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT p.id, p.proyecto_id, p.comentario, p.descripcion,
                       p.fecha_plazo, p.estado, p.prioridad, p.responsable,
                       p.creado_por, p.fecha_creacion, u.nombre as nombre_creador
                FROM proximos_pasos p
                LEFT JOIN users u ON u.user_id = p.creado_por
                WHERE p.proyecto_id = %s ORDER BY p.fecha_plazo ASC
            """, (pid,))
            pasos = cur.fetchall()
            for paso in pasos:
                if paso.get("fecha_plazo"):
                    paso["fecha_plazo"] = paso["fecha_plazo"].isoformat()
                if paso.get("fecha_creacion"):
                    paso["fecha_creacion"] = paso["fecha_creacion"].isoformat()
        return jsonify({"proximos_pasos": pasos})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error listando proximos_pasos: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/<int:pid>/proximos_pasos", methods=["POST"])
@session_required
def crear_proximo_paso(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()
        comentario = data.get("comentario")
        fecha_plazo = data.get("fecha_plazo")
        if not comentario or not fecha_plazo:
            return jsonify({"message": "Falta comentario o fecha_plazo"}), 400

        descripcion = data.get("descripcion", "")
        estado = data.get("estado", "PENDIENTE")
        prioridad = data.get("prioridad", "MEDIA")
        responsable = data.get("responsable", "")

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proximos_pasos
                (proyecto_id, comentario, descripcion, fecha_plazo, estado, prioridad, responsable, creado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (pid, comentario, descripcion, fecha_plazo, estado, prioridad, responsable, current_user_id))
            nuevo_id = cur.fetchone()[0]
        conn.commit()

        log_control(current_user_id, "crear_proximo_paso", modulo="proyectos",
                    entidad_tipo="proximo_paso", entidad_id=nuevo_id,
                    entidad_nombre=comentario[:50], exitoso=True, detalle=f"Proyecto {pid}")
        return jsonify({"message": "Próximo paso creado", "id": nuevo_id}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error creando proximo_paso: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/proximos_pasos/<int:paso_id>", methods=["PUT"])
@session_required
def actualizar_proximo_paso(current_user_id, paso_id):
    conn = None
    try:
        data = request.get_json()
        fields, vals = [], []
        allowed = ["comentario", "descripcion", "fecha_plazo", "estado", "prioridad", "responsable"]
        for k in allowed:
            if k in data:
                fields.append(f"{k} = %s")
                vals.append(data[k])
        if not fields:
            return jsonify({"message": "Sin datos para actualizar"}), 400

        vals.append(paso_id)
        sql = f"UPDATE proximos_pasos SET {', '.join(fields)} WHERE id = %s"
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, tuple(vals))
        conn.commit()

        log_control(current_user_id, "editar_proximo_paso", modulo="proyectos",
                    entidad_tipo="proximo_paso", entidad_id=paso_id, exitoso=True)
        return jsonify({"message": "Próximo paso actualizado"})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error actualizando proximo_paso: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@documentos_bp.route("/proyectos/proximos_pasos/<int:paso_id>", methods=["DELETE"])
@session_required
def eliminar_proximo_paso(current_user_id, paso_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM proximos_pasos WHERE id = %s RETURNING id", (paso_id,))
            deleted = cur.fetchone()
        conn.commit()
        if not deleted:
            return jsonify({"message": "Próximo paso no encontrado"}), 404

        log_control(current_user_id, "eliminar_proximo_paso", modulo="proyectos",
                    entidad_tipo="proximo_paso", entidad_id=paso_id, exitoso=True)
        return jsonify({"message": "Próximo paso eliminado"})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error eliminando proximo_paso: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)
