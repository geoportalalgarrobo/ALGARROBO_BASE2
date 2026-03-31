"""
Módulo de auditoría y registro de actividad.
Funciones log_control y log_auditoria centralizadas.
"""
import json as _json
from flask import request
from core.config import logger
from core.database import get_db_connection, release_db_connection


def log_control(user_id, accion, modulo='proyectos',
                entidad_tipo=None, entidad_id=None, entidad_nombre=None,
                exitoso=True, detalle=None,
                datos_antes=None, datos_despues=None):
    """
    Registra cada acción del usuario en control_actividad con contexto completo.
    Se llama desde los endpoints de API tras cada operación.
    """
    conn = None
    try:
        ip = None
        ua = None
        ep = None
        try:
            ip = request.remote_addr
            ua = request.headers.get('User-Agent', '')[:500]
            ep = request.path[:200]
        except RuntimeError:
            pass  # fuera de contexto de request (ej. triggers)

        conn = get_db_connection()
        if not conn:
            return
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO control_actividad
                    (user_id, accion, modulo,
                     entidad_tipo, entidad_id, entidad_nombre,
                     exitoso, detalle,
                     ip_origen, user_agent, endpoint,
                     datos_antes, datos_despues)
                VALUES (%s,%s,%s, %s,%s,%s, %s,%s, %s,%s,%s, %s,%s)
            """, (
                user_id, accion, modulo,
                entidad_tipo, entidad_id, entidad_nombre,
                exitoso, detalle,
                ip, ua, ep,
                _json.dumps(datos_antes, default=str) if datos_antes else None,
                _json.dumps(datos_despues, default=str) if datos_despues else None
            ))
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error en log_control: {e}")
    finally:
        if conn:
            release_db_connection(conn)


def log_auditoria(user_id, accion, descripcion):
    """Auditoría legacy + registro en módulo de control."""
    modulo = 'auth' if any(k in accion for k in ('login', 'logout', 'password')) else \
             'usuarios' if 'user' in accion else 'proyectos'
    log_control(user_id, accion, modulo=modulo, detalle=descripcion)

    # Mantener escritura en tabla legacy auditoria
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auditoria (user_id, accion, descripcion) VALUES (%s, %s, %s)",
                (user_id, accion, descripcion)
            )
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error en auditoría legacy: {e}")
    finally:
        if conn:
            release_db_connection(conn)


def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    from core.config import ALLOWED_EXTENSIONS
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
