"""
Gestión de sesiones JWT: crear, validar y revocar tokens.
"""
from datetime import datetime, timedelta
import jwt
from core.config import JWT_SECRET, SESSION_EXPIRY_HOURS, logger
from core.database import get_db_connection, release_db_connection


def create_session(user_id):
    """Crea un JWT firmado con expiración automática."""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def validate_session(token):
    """
    Valida un token JWT y revisa la blocklist en BD.
    Retorna user_id o None.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS jwt_blocklist (
                        token TEXT PRIMARY KEY,
                        fecha TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("SELECT 1 FROM jwt_blocklist WHERE token = %s", (token,))
                if cur.fetchone():
                    return None
        finally:
            release_db_connection(conn)
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        logger.warning("Token JWT expirado")
        return None
    except jwt.InvalidTokenError:
        return None


def remove_session(token):
    """Agrega un token a la blocklist (logout)."""
    if not token:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jwt_blocklist (
                    token TEXT PRIMARY KEY,
                    fecha TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute(
                "INSERT INTO jwt_blocklist (token) VALUES (%s) ON CONFLICT DO NOTHING",
                (token,)
            )
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error blocklist: {e}")
    finally:
        release_db_connection(conn)


def cleanup_expired_sessions():
    """
    Limpia tokens expirados de la blocklist.
    SEGURIDAD [H-20]: Implementación real en lugar de pass.
    Llamar periódicamente (ej: cron, APScheduler).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Eliminar tokens de la blocklist más viejos que 2x SESSION_EXPIRY
            # (ya que un token expirado no necesita estar en la blocklist)
            cur.execute("""
                DELETE FROM jwt_blocklist
                WHERE fecha < NOW() - INTERVAL '%s hours'
            """, (SESSION_EXPIRY_HOURS * 2,))
            deleted = cur.rowcount
        conn.commit()
        if deleted > 0:
            logger.info(f"Limpieza blocklist: {deleted} tokens expirados eliminados")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error en cleanup_expired_sessions: {e}")
    finally:
        release_db_connection(conn)
