"""
Gestión del pool de conexiones a PostgreSQL.
Encapsula init, get, release y cleanup del pool de conexiones.
"""
import threading
import psycopg2
import psycopg2.pool
from core.config import DB_CONNECTION_STRING, logger

# ─── Pool global ───────────────────────────────────────────────
connection_pool = None
pool_lock = threading.RLock()


def init_connection_pool(max_retries=1):
    """
    Inicializa el pool de conexiones a la base de datos.
    Optimizado para Railway (PostgreSQL).
    """
    global connection_pool

    try:
        with pool_lock:
            if connection_pool and not connection_pool.closed:
                try:
                    connection_pool.closeall()
                    logger.info("Pool anterior cerrado correctamente")
                except Exception as e:
                    logger.warning(f"Error cerrando pool anterior: {e}")

            connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=DB_CONNECTION_STRING,
                keepalives=1,
                keepalives_idle=60,
                keepalives_interval=10,
                keepalives_count=5,
                connect_timeout=10,
                application_name="municipal_api_railway"
            )

            # Verificar que el pool funciona
            test_conn = connection_pool.getconn()
            with test_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            connection_pool.putconn(test_conn)

            logger.info("Pool de conexiones inicializado correctamente (Optimizado para Railway)")
            return True

    except Exception as e:
        logger.error(f"Error en la inicialización del pool: {e}")
        connection_pool = None
        return False


def get_db_connection():
    """Obtiene una conexión del pool, re-inicializando si es necesario."""
    global connection_pool

    try:
        if connection_pool is None or connection_pool.closed:
            logger.info("Pool no disponible, inicializando...")
            if not init_connection_pool():
                raise Exception("No se pudo inicializar el pool de conexiones")

        conn = connection_pool.getconn()

        # Validar que la conexión sigue activa
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        except Exception:
            logger.warning("Descartando conexion inactiva")
            connection_pool.putconn(conn, close=True)
            conn = connection_pool.getconn()

        return conn
    except Exception as e:
        logger.error(f"Error obteniendo conexión: {e}")
        raise e


def release_db_connection(conn):
    """Devuelve una conexión al pool de forma segura."""
    try:
        if connection_pool and conn:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Error al devolver la conexión al pool: {e}")
        try:
            conn.close()
        except:
            pass


def cleanup_pool():
    """Cierra el pool de conexiones al terminar la aplicación."""
    global connection_pool

    try:
        with pool_lock:
            if connection_pool and not connection_pool.closed:
                connection_pool.closeall()
                logger.info("Pool de conexiones cerrado correctamente")
    except Exception as e:
        logger.error(f"Error al cerrar el pool de conexiones: {e}")
