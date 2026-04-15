"""
Blueprint: API Mobile – Registro, Login, Reportes, Fotos, Perfil,
           Categorías, Comentarios, Maestros, Admin (Crear Funcionario),
           Migración de Volumen
Rutas: /api/mobile/*, /api/admin/*, /api/volume/*
"""
import os
import io
import time
import tempfile
import zipfile
import traceback
import bcrypt
import psycopg2.extras
from datetime import datetime
from flask import Blueprint, request, jsonify, send_from_directory, send_file, after_this_request
from werkzeug.utils import secure_filename
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from core.config import logger, DOCS_FOLDER, FOTOS_DIR, AUDIT_OUT_DIR, FOTOS_OUT_DIR
from core.database import get_db_connection, release_db_connection
from utils.auth_utils import create_session
from utils.decorators import session_required, admin_required
from utils.audit_logger import log_auditoria, log_control

mobile_bp = Blueprint('mobile', __name__)


# ─── Utilidades de imagen ──────────────────────────────────────

def es_imagen(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}


def optimizar_imagen(data):
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = bg
        if max(img.size) > 1920:
            img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format='JPEG', quality=85, optimize=True)
        return out.getvalue()
    except:
        return data


def extraer_gps(data):
    try:
        img = Image.open(io.BytesIO(data))
        exif = img._getexif()
        meta = {'ancho_px': img.width, 'alto_px': img.height}
        if not exif:
            return meta

        gps = {}
        for tag_id, val in exif.items():
            if TAGS.get(tag_id) == 'GPSInfo':
                for gps_id in val:
                    gps[GPSTAGS.get(gps_id, gps_id)] = val[gps_id]

        if 'GPSLatitude' in gps and 'GPSLongitude' in gps:
            def to_dec(coords, ref):
                d = float(coords[0]) + float(coords[1]) / 60 + float(coords[2]) / 3600
                return -d if ref in ['S', 'W'] else d
            meta['latitud'] = to_dec(gps['GPSLatitude'], gps.get('GPSLatitudeRef', 'N'))
            meta['longitud'] = to_dec(gps['GPSLongitude'], gps.get('GPSLongitudeRef', 'E'))

        dt_val = exif.get('DateTimeOriginal') or exif.get('DateTime')
        if dt_val:
            try:
                meta['fecha_captura'] = datetime.strptime(dt_val, '%Y:%m:%d %H:%M:%S')
            except:
                pass
        return meta
    except:
        return {}



# ─── REGISTRO ─────────────────────────────────────────────────

@mobile_bp.route("/mobile/auth/register", methods=["POST"])
def registrar():
    conn = None
    try:
        d = request.get_json()
        if not all(k in d for k in ['email', 'password', 'nombre']):
            return jsonify({"msg": "Falta email, password o nombre"}), 400

        email = d['email'].strip().lower()
        pwd = d['password']
        nom = d['nombre'].strip()
        if len(pwd) < 6:
            return jsonify({"msg": "Password mínimo 6 caracteres"}), 400

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SELECT 1 FROM users WHERE email=%s", (email,))
            if c.fetchone():
                return jsonify({"msg": "Email ya registrado"}), 400

        phash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""INSERT INTO users (email, password_hash, nombre, nivel_acceso, activo)
                        VALUES (%s, %s, %s, 0, TRUE) RETURNING user_id""",
                      (email, phash, nom))
            user_id = c.fetchone()['user_id']
            c.execute("SELECT role_id FROM roles WHERE nombre = 'Vecino'")
            role_row = c.fetchone()
            if role_row:
                c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                          (user_id, role_row['role_id']))
        conn.commit()
        return jsonify({"msg": "Registro exitoso", "user_id": user_id}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error registro: {e}")
        return jsonify({"msg": "Error al registrar"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── ADMIN: CREAR FUNCIONARIO ─────────────────────────────────

@mobile_bp.route("/admin/crear-funcionario", methods=["POST"])
@admin_required
def crear_funcionario(current_user_id):
    conn = None
    try:
        d = request.get_json()
        if not all(k in d for k in ['email', 'password', 'nombre']):
            return jsonify({"msg": "Faltan datos"}), 400

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            email = d['email'].strip().lower()
            pwd = d['password']
            nom = d['nombre'].strip()
            c.execute("SELECT 1 FROM users WHERE email=%s", (email,))
            if c.fetchone():
                return jsonify({"msg": "Email ya registrado"}), 400

            phash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
            c.execute("""INSERT INTO users (email, password_hash, nombre, nivel_acceso, activo)
                        VALUES (%s, %s, %s, 1, TRUE) RETURNING user_id""",
                      (email, phash, nom))
            new_user_id = c.fetchone()['user_id']

            c.execute("SELECT role_id FROM roles WHERE nombre IN ('Fiscalizador', 'Funcionario') LIMIT 1")
            role_row = c.fetchone()
            if not role_row:
                c.execute("INSERT INTO roles (nombre) VALUES ('Fiscalizador') RETURNING role_id")
                role_row = c.fetchone()

            c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                      (new_user_id, role_row['role_id']))

            conn.commit()
            return jsonify({"msg": "Funcionario creado exitosamente", "user_id": new_user_id}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error crear funcionario: {e}")
        return jsonify({"msg": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── LOGIN MOBILE ─────────────────────────────────────────────

@mobile_bp.route("/mobile/auth/login", methods=["POST"])
def login_mobile():
    conn = None
    try:
        d = request.get_json()
        email = d.get('email', '').strip().lower()
        pwd = d.get('password', '')

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT user_id, email, nombre, password_hash, activo, nivel_acceso
                        FROM users WHERE email=%s""", (email,))
            u = c.fetchone()

        if not u or not u['activo'] or not bcrypt.checkpw(pwd.encode(), u['password_hash'].encode()):
            return jsonify({"msg": "Credenciales inválidas"}), 401

        token = create_session(u['user_id'])
        nivel = u['nivel_acceso'] if u['nivel_acceso'] is not None else 0

        return jsonify({
            "token": token,
            "user": {
                "user_id": u['user_id'], "email": u['email'],
                "nombre": u['nombre'], "nivel_acceso": int(nivel), "roles": []
            }
        }), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Login error: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── MAESTROS MOBILE ──────────────────────────────────────────

@mobile_bp.route("/mobile/divisiones", methods=["GET"])
def get_divisiones_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT division_id, nombre FROM divisiones ORDER BY nombre")
            return jsonify(cur.fetchall()), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error divisiones: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/roles", methods=["GET"])
def get_roles_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT role_id, nombre FROM roles ORDER BY nombre")
            return jsonify(cur.fetchall()), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error roles: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/estados", methods=["GET"])
def get_estados_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, nombre FROM estados_reporte ORDER BY id")
            return jsonify(cur.fetchall()), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/gravedades", methods=["GET"])
def get_gravedades_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, nombre FROM reportes_gravedad ORDER BY id")
            return jsonify(cur.fetchall()), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/categorias", methods=["GET"])
def get_categorias_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, nombre FROM categorias_reporte ORDER BY id")
            return jsonify(cur.fetchall()), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── PERFIL & ESTADÍSTICAS ────────────────────────────────────

@mobile_bp.route("/mobile/perfil", methods=["GET"])
@session_required
def get_perfil(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SELECT user_id, nombre, email, nivel_acceso FROM users WHERE user_id = %s",
                      (current_user_id,))
            user = c.fetchone()
            c.execute("""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE estado_id = 1) as pendientes,
                       COUNT(*) FILTER (WHERE estado_id IN (2,3)) as en_proceso,
                       COUNT(*) FILTER (WHERE estado_id = 4) as resueltos
                FROM reportes_ciudadanos
                WHERE reportado_por = %s AND activo = TRUE
            """, (current_user_id,))
            stats = c.fetchone()
        return jsonify({"user": user, "stats": stats}), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error perfil: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/perfil", methods=["PUT"])
@session_required
def update_perfil(current_user_id):
    conn = None
    try:
        d = request.get_json()
        nombre = d.get('nombre')
        pwd = d.get('password')
        updates, vals = [], []
        if nombre:
            updates.append("nombre = %s")
            vals.append(nombre)
        if pwd and len(pwd) >= 6:
            phash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
            updates.append("password_hash = %s")
            vals.append(phash)
        if not updates:
            return jsonify({"msg": "Nada que actualizar"}), 400

        vals.append(current_user_id)
        conn = get_db_connection()
        with conn.cursor() as c:
            c.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s", tuple(vals))
        conn.commit()
        return jsonify({"msg": "Perfil actualizado"}), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error update perfil: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── REPORTES CIUDADANOS ──────────────────────────────────────

@mobile_bp.route("/mobile/reportes", methods=["POST"])
@session_required
def crear_reporte(current_user_id):
    conn = None
    try:
        d = request.get_json()
        required = ['categoria_id', 'latitud', 'longitud', 'direccion_referencia']
        if not all(k in d for k in required):
            return jsonify({"msg": "Faltan campos"}), 400

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""INSERT INTO reportes_ciudadanos
                        (categoria_id, estado_id, gravedad_id, latitud, longitud,
                         direccion_referencia, descripcion, reportado_por, activo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                        RETURNING id, numero_folio""",
                      (d['categoria_id'], 1, d.get('gravedad_id', 1), d['latitud'],
                       d['longitud'], d['direccion_referencia'],
                       d.get('descripcion'), current_user_id))
            result = c.fetchone()
        conn.commit()
        return jsonify({"msg": "Creado", "id": result['id'],
                        "numero_folio": result['numero_folio']}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error crear reporte: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/reportes/<int:rid>", methods=["GET"])
@session_required
def get_reporte_detalle(current_user_id, rid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT r.id, r.numero_folio,
                        c.nombre as categoria, e.nombre as estado, g.nombre as gravedad,
                        r.categoria_id, r.estado_id, r.gravedad_id,
                        r.direccion_referencia, r.descripcion, r.revisado,
                        r.fecha_reporte, r.fecha_actualizacion, r.latitud, r.longitud,
                        u_rep.nombre as reportado_por_nombre, u_rep.email as reportado_por_email,
                        u_act.nombre as actualizado_por_nombre, u_act.email as actualizado_por_email
                        FROM reportes_ciudadanos r
                        LEFT JOIN categorias_reporte c ON c.id = r.categoria_id
                        LEFT JOIN estados_reporte e ON e.id = r.estado_id
                        LEFT JOIN reportes_gravedad g ON g.id = r.gravedad_id
                        LEFT JOIN users u_rep ON u_rep.user_id = r.reportado_por
                        LEFT JOIN users u_act ON u_act.user_id = r.actualizado_por
                        WHERE r.id = %s""", (rid,))
            repo = c.fetchone()
        if not repo:
            return jsonify({"msg": "No encontrado"}), 404
        return jsonify(repo), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error detalle reporte: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/reportes/todos", methods=["GET"])
def get_todos_reportes():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT r.id, r.numero_folio, r.latitud, r.longitud,
                        c.nombre as categoria, e.nombre as estado, g.nombre as gravedad,
                        r.estado_id, r.gravedad_id, r.direccion_referencia, r.categoria_id,
                        r.descripcion, r.revisado, r.fecha_reporte, r.fecha_actualizacion,
                        u_rep.nombre as reportado_por_nombre, u_rep.email as reportado_por_email,
                        u_act.nombre as actualizado_por_nombre, u_act.email as actualizado_por_email
                        FROM reportes_ciudadanos r
                        LEFT JOIN categorias_reporte c ON c.id = r.categoria_id
                        LEFT JOIN estados_reporte e ON e.id = r.estado_id
                        LEFT JOIN reportes_gravedad g ON g.id = r.gravedad_id
                        LEFT JOIN users u_rep ON u_rep.user_id = r.reportado_por
                        LEFT JOIN users u_act ON u_act.user_id = r.actualizado_por
                        WHERE r.activo = TRUE ORDER BY r.fecha_reporte DESC""")
            rows = c.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error mapa: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/reportes/mis-reportes", methods=["GET"])
@session_required
def mis_reportes(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT r.id, r.numero_folio, c.nombre as categoria, e.nombre as estado,
                        r.direccion_referencia, r.descripcion, r.fecha_reporte
                        FROM reportes_ciudadanos r
                        LEFT JOIN categorias_reporte c ON c.id = r.categoria_id
                        LEFT JOIN estados_reporte e ON e.id = r.estado_id
                        WHERE r.reportado_por = %s AND r.activo = TRUE
                        ORDER BY r.fecha_reporte DESC""", (current_user_id,))
            reportes = c.fetchall()
        return jsonify(reportes), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error mis reportes: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── COMENTARIOS ──────────────────────────────────────────────

@mobile_bp.route("/mobile/reportes/<int:rid>/comentarios", methods=["GET"])
def get_comentarios(rid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT rc.id, rc.comentario, rc.creado_en, u.nombre as autor
                        FROM reportes_comentarios rc
                        JOIN users u ON u.user_id = rc.user_id
                        WHERE rc.reporte_id = %s ORDER BY rc.creado_en""", (rid,))
            rows = c.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error comments get: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/reportes/<int:rid>/comentarios", methods=["POST"])
@session_required
def add_comentario(current_user_id, rid):
    conn = None
    try:
        d = request.get_json()
        texto = d.get('comentario')
        if not texto:
            return jsonify({"msg": "Texto vacío"}), 400

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("INSERT INTO reportes_comentarios (reporte_id, user_id, comentario) VALUES (%s, %s, %s) RETURNING id",
                      (rid, current_user_id, texto))
            nid = c.fetchone()['id']
        conn.commit()
        return jsonify({"msg": "Comentario agregado", "id": nid}), 201
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error comments post: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── ACTUALIZACIÓN ESTADO/GRAVEDAD ────────────────────────────

@mobile_bp.route("/mobile/reportes/<int:rid>/actualizar", methods=["POST"])
@session_required
def actualizar_reporte(current_user_id, rid):
    conn = None
    try:
        d = request.get_json()
        updates, vals = [], []
        for k in ['estado_id', 'gravedad_id', 'categoria_id']:
            if k in d:
                updates.append(f"{k} = %s")
                vals.append(int(d[k]))
        if 'revisado' in d:
            updates.append("revisado = %s")
            vals.append(bool(d['revisado']))
        for k in ['direccion_referencia', 'descripcion']:
            if k in d:
                updates.append(f"{k} = %s")
                vals.append(d[k])
        if not updates:
            return jsonify({"msg": "Nada que actualizar"}), 400

        updates.append("actualizado_por = %s")
        vals.append(current_user_id)
        updates.append("fecha_actualizacion = NOW()")
        vals.append(rid)

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute(f"UPDATE reportes_ciudadanos SET {', '.join(updates)} WHERE id = %s RETURNING id",
                      tuple(vals))
            result = c.fetchone()
            if not result:
                return jsonify({"msg": "Reporte no encontrado"}), 404
        conn.commit()
        return jsonify({"msg": "Reporte actualizado"}), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error actualizar reporte: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/reportes/<int:rid>/verificar", methods=["POST"])
@session_required
def verificar_reporte(current_user_id, rid):
    return actualizar_reporte(current_user_id, rid)


# ─── FOTOS ────────────────────────────────────────────────────

@mobile_bp.route("/mobile/reportes/<int:rid>/fotos", methods=["GET"])
def ver_fotos_reporte(rid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SELECT id, ruta_archivo FROM reportes_fotos WHERE reporte_id = %s", (rid,))
            fotos = c.fetchall()
        return jsonify(fotos), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error ver fotos: {e}")
        return jsonify({"msg": "Error"}), 500
    finally:
        if conn: release_db_connection(conn)


@mobile_bp.route("/mobile/reportes/<int:rid>/fotos", methods=["POST"])
@session_required
def subir_fotos(current_user_id, rid):
    conn = None
    try:
        files = request.files.getlist('fotos')
        if not files:
            return jsonify({"msg": "Sin fotos recibidas"}), 400

        conn = get_db_connection()
        guardadas = []
        ym = time.strftime("%Y/%m")
        udir = os.path.join(FOTOS_DIR, ym)
        os.makedirs(udir, exist_ok=True)

        for i, f in enumerate(files):
            if not f:
                continue
            ts = int(time.time() * 1000) + i
            fname = secure_filename(f"rep_{rid}_{ts}_{f.filename}")
            fpath = os.path.join(udir, fname)
            f.save(fpath)

            url = f"/fotos_reportes/{ym}/{fname}"
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
                c.execute("INSERT INTO reportes_fotos (reporte_id, ruta_archivo, subido_por) VALUES (%s, %s, %s) RETURNING id",
                          (rid, url, current_user_id))
                fid = c.fetchone()['id']
            guardadas.append({"id": fid, "url": url})

        conn.commit()
        return jsonify({"msg": f"{len(guardadas)} fotos subidas", "fotos": guardadas}), 200
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error subida fotos: {e}", exc_info=True)
        return jsonify({"msg": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


# ─── MIGRACIÓN DE VOLUMEN ─────────────────────────────────────

@mobile_bp.route('/volume/export', methods=['GET'])
@admin_required
def volume_export(current_user_id):
    """
    Genera un ZIP de todos los assets del servidor y lo devuelve como descarga.
    Escribe a archivo temporal para no agotar la RAM con datasets grandes.
    Requiere nivel_acceso >= 10 (@admin_required).
    """
    tmp_path = None
    try:
        items_to_backup = {
            "docs": DOCS_FOLDER,
            "auditoria_reportes": AUDIT_OUT_DIR,
            "fotos_reportes": FOTOS_OUT_DIR,
        }

        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.zip')
        os.close(tmp_fd)

        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for folder_name, full_path in items_to_backup.items():
                if os.path.exists(full_path) and os.path.isdir(full_path):
                    for root, dirs, files in os.walk(full_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join(folder_name, os.path.relpath(file_path, full_path))
                            zf.write(file_path, arcname)

        log_auditoria(current_user_id, "volume_export",
                      f"Exportación de volumen completa desde {request.remote_addr}")

        @after_this_request
        def _remove_tmp(response):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return response

        return send_file(
            tmp_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
        )
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        logger.error(f"Error en exportación de volumen: {e}")
        return jsonify({"message": "Error interno"}), 500


@mobile_bp.route('/volume/import', methods=['POST'])
@admin_required
def volume_import(current_user_id):
    """
    Importa un ZIP de assets al servidor extrayendo archivo por archivo
    para prevenir path traversal y evitar symlinks maliciosos.
    Requiere nivel_acceso >= 10 (@admin_required).
    """
    if 'file' not in request.files:
        return jsonify({"message": "No hay archivo"}), 400

    file = request.files['file']
    if not file.filename.lower().endswith('.zip'):
        return jsonify({"message": "Solo se aceptan archivos ZIP"}), 400

    try:
        BASE_TARGET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists("/data") and os.path.isdir("/data"):
            BASE_TARGET = "/data"

        base_real = os.path.realpath(BASE_TARGET)
        ALLOWED_FOLDERS = {"docs", "auditoria_reportes", "fotos_reportes"}
        extracted = 0

        with zipfile.ZipFile(file) as zf:
            for info in zf.infolist():
                member = info.filename
                clean_member = member.replace("\\", "/").strip("/")
                parts = clean_member.split("/")

                # Rechazar path traversal
                if ".." in parts or not parts[0]:
                    return jsonify({"message": f"Ruta no permitida detectada: {member}"}), 400

                # Rechazar carpetas fuera de la lista blanca
                if parts[0] not in ALLOWED_FOLDERS:
                    return jsonify({
                        "message": f"Carpeta no permitida: '{parts[0]}'. Permitidas: {', '.join(sorted(ALLOWED_FOLDERS))}"
                    }), 400

                # Ignorar entradas de directorio
                if member.endswith("/"):
                    continue

                # Ignorar symlinks dentro del ZIP
                if (info.external_attr >> 16) == 0o120777:
                    logger.warning(f"Symlink ignorado en ZIP: {member}")
                    continue

                # Verificar que la ruta final quede dentro del árbol permitido
                target_path = os.path.realpath(os.path.join(BASE_TARGET, clean_member))
                if not target_path.startswith(base_real + os.sep):
                    return jsonify({"message": f"Ruta maliciosa detectada: {member}"}), 400

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zf.open(info) as src, open(target_path, 'wb') as dst:
                    dst.write(src.read())
                extracted += 1

        log_auditoria(current_user_id, "volume_import",
                      f"Importación de {extracted} archivos desde {request.remote_addr}")
        logger.info(f"Importación completada por user_id={current_user_id}: {extracted} archivos en {BASE_TARGET}")
        return jsonify({"message": f"Importación completada: {extracted} archivos procesados."}), 200

    except zipfile.BadZipFile:
        return jsonify({"message": "El archivo no es un ZIP válido"}), 400
    except Exception as e:
        logger.error(f"Error en importación de volumen: {e}", exc_info=True)
        return jsonify({"message": "Error durante la importación. Revise los logs del servidor."}), 500
