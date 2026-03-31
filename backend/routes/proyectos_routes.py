"""
Blueprint: Proyectos y Catálogos CRUD
Rutas: /proyectos/*, /areas/*, /financiamientos/*, /sectores/*,
       /lineamientos_estrategicos/*, /etapas_proyecto/*, /estados_proyecto/*,
       /estados_postulacion/*
"""
import traceback
from datetime import datetime
import psycopg2.extras
from flask import Blueprint, request, jsonify

from core.config import logger, ALLOWED_TABLES_READ
from core.database import get_db_connection, release_db_connection
from utils.decorators import session_required
from utils.audit_logger import log_auditoria, log_control

proyectos_bp = Blueprint('proyectos', __name__)


# ─── Helpers genéricos de CRUD ─────────────────────────────────

def crud_simple(tabla, current_user_id):
    """
    SEGURIDAD [H-07]: Validación de tabla contra lista blanca.
    """
    if tabla not in ALLOWED_TABLES_READ:
        return jsonify({"message": "Tabla no permitida"}), 403

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT * FROM {tabla}")
            rows = cur.fetchall()
        return jsonify(rows)
    finally:
        release_db_connection(conn)


def generic_create(table_name, data, extra_columns=None):
    if table_name not in ALLOWED_TABLES_READ:
        raise ValueError(f"Tabla '{table_name}' no en lista blanca")

    if extra_columns is None:
        extra_columns = []

    columns = ["nombre"] + extra_columns
    values = [data.get("nombre")] + [data.get(col) for col in extra_columns]
    placeholders = ", ".join(["%s"] * len(columns))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({placeholders})
                RETURNING id
            """
            cur.execute(query, values)
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id
    finally:
        release_db_connection(conn)


def generic_update(table_name, id, data, extra_columns=None):
    if table_name not in ALLOWED_TABLES_READ:
        raise ValueError(f"Tabla '{table_name}' no en lista blanca")

    if extra_columns is None:
        extra_columns = []

    set_clauses = ["nombre = %s", "activo = %s"]
    values = [data.get("nombre"), data.get("activo", True)]

    for col in extra_columns:
        set_clauses.append(f"{col} = %s")
        values.append(data.get(col))

    values.append(id)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = f"""
                UPDATE {table_name}
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """
            cur.execute(query, values)
        conn.commit()
    finally:
        release_db_connection(conn)


def generic_delete(table_name, id):
    if table_name not in ALLOWED_TABLES_READ:
        raise ValueError(f"Tabla '{table_name}' no en lista blanca")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE {table_name} SET activo = FALSE WHERE id = %s", (id,))
        conn.commit()
    finally:
        release_db_connection(conn)


# ─── PROYECTOS ─────────────────────────────────────────────────

@proyectos_bp.route("/proyectos4", methods=["GET"])
@session_required
def get_proyectos4(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    p.*,
                    GREATEST(
                        p.fecha_actualizacion,
                        (SELECT MAX(creado_en) FROM proyectos_hitos WHERE proyecto_id = p.id),
                        (SELECT MAX(creado_en) FROM proyectos_observaciones WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_subida) FROM proyectos_documentos WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_creacion) FROM proyectos_geomapas WHERE proyecto_id = p.id)
                    ) AS ult_modificacion,
                    u.nombre AS user_nombre,
                    ua.nombre AS actualizado_por_nombre,
                    a.id AS area_id, a.nombre AS area_nombre,
                    le.id AS lineamiento_id, le.nombre AS lineamiento_nombre,
                    le.nombre AS lineamiento_estrategico_nombre,
                    f.id AS financiamiento_id,
                    COALESCE(f.fuente, f.nombre) AS financiamiento_nombre,
                    ep.id AS etapa_id, ep.nombre AS etapa_nombre,
                    es.id AS estado_id, es.nombre AS estado_nombre, es.color AS estado_color,
                    epost.id AS estado_postulacion_id, epost.nombre AS estado_postulacion_nombre,
                    s.id AS sector_id, s.nombre AS sector_nombre
                FROM proyectos p
                INNER JOIN users u ON u.user_id = p.user_id
                LEFT JOIN users ua ON ua.user_id = p.actualizado_por
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN lineamientos_estrategicos le ON le.id = p.lineamiento_estrategico_id
                LEFT JOIN financiamientos f ON f.id = p.financiamiento_id
                LEFT JOIN etapas_proyecto ep ON ep.id = p.etapa_proyecto_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                LEFT JOIN estados_postulacion epost ON epost.id = p.estado_postulacion_id
                LEFT JOIN sectores s ON s.id = p.sector_id
            """)
            proyectos = cur.fetchall()
        return jsonify(proyectos)
    finally:
        if conn:
            release_db_connection(conn)


@proyectos_bp.route("/proyectos_chat", methods=["GET"])
@session_required
def get_proyectos_chat(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    p.*,
                    GREATEST(
                        p.fecha_actualizacion,
                        (SELECT MAX(creado_en) FROM proyectos_hitos WHERE proyecto_id = p.id),
                        (SELECT MAX(creado_en) FROM proyectos_observaciones WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_subida) FROM proyectos_documentos WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_creacion) FROM proyectos_geomapas WHERE proyecto_id = p.id)
                    ) AS ult_modificacion,
                    a.nombre AS area,
                    le.nombre AS lineamiento,
                    COALESCE(f.fuente, f.nombre) AS financiamiento,
                    ep.nombre AS etapa,
                    es.nombre AS estado,
                    epost.nombre AS estado_postulacion,
                    s.nombre AS sector
                FROM proyectos p
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN lineamientos_estrategicos le ON le.id = p.lineamiento_estrategico_id
                LEFT JOIN financiamientos f ON f.id = p.financiamiento_id
                LEFT JOIN etapas_proyecto ep ON ep.id = p.etapa_proyecto_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                LEFT JOIN estados_postulacion epost ON epost.id = p.estado_postulacion_id
                LEFT JOIN sectores s ON s.id = p.sector_id
            """)
            proyectos = cur.fetchall()
        return jsonify(proyectos)
    finally:
        if conn:
            release_db_connection(conn)


@proyectos_bp.route("/proyectos", methods=["GET"])
@session_required
def get_proyectos(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    p.*,
                    GREATEST(
                        p.fecha_actualizacion,
                        (SELECT MAX(creado_en) FROM proyectos_hitos WHERE proyecto_id = p.id),
                        (SELECT MAX(creado_en) FROM proyectos_observaciones WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_subida) FROM proyectos_documentos WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_creacion) FROM proyectos_geomapas WHERE proyecto_id = p.id)
                    ) AS ult_modificacion,
                    u.nombre AS user_nombre,
                    ua.nombre AS actualizado_por_nombre,
                    a.id AS area_id, a.nombre AS area_nombre,
                    le.id AS lineamiento_id, le.nombre AS lineamiento_nombre,
                    le.nombre AS lineamiento_estrategico_nombre,
                    f.id AS financiamiento_id,
                    COALESCE(f.fuente, f.nombre) AS financiamiento_nombre,
                    ep.id AS etapa_id, ep.nombre AS etapa_nombre,
                    es.id AS estado_id, es.nombre AS estado_nombre, es.color AS estado_color,
                    epost.id AS estado_postulacion_id, epost.nombre AS estado_postulacion_nombre,
                    s.id AS sector_id, s.nombre AS sector_nombre,
                    COALESCE(
                        json_agg(
                            DISTINCT jsonb_build_object(
                                'id', h.id, 'fecha', h.fecha, 'observacion', h.observacion,
                                'creado_por', h.creado_por, 'nombre_creador', hu.nombre,
                                'creado_en', h.creado_en
                            )
                        ) FILTER (WHERE h.id IS NOT NULL), '[]'
                    ) AS hitos_lista,
                    COALESCE(
                        json_agg(
                            DISTINCT jsonb_build_object(
                                'id', o.id, 'fecha', o.fecha, 'observacion', o.observacion,
                                'creado_por', o.creado_por, 'nombre_creador', ou.nombre,
                                'creado_en', o.creado_en
                            )
                        ) FILTER (WHERE o.id IS NOT NULL), '[]'
                    ) AS observaciones_lista
                FROM proyectos p
                INNER JOIN users u ON u.user_id = p.user_id
                LEFT JOIN users ua ON ua.user_id = p.actualizado_por
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN lineamientos_estrategicos le ON le.id = p.lineamiento_estrategico_id
                LEFT JOIN financiamientos f ON f.id = p.financiamiento_id
                LEFT JOIN etapas_proyecto ep ON ep.id = p.etapa_proyecto_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                LEFT JOIN estados_postulacion epost ON epost.id = p.estado_postulacion_id
                LEFT JOIN sectores s ON s.id = p.sector_id
                LEFT JOIN proyectos_hitos h ON h.proyecto_id = p.id
                LEFT JOIN users hu ON hu.user_id = h.creado_por
                LEFT JOIN proyectos_observaciones o ON o.proyecto_id = p.id
                LEFT JOIN users ou ON ou.user_id = o.creado_por
                GROUP BY
                    p.id, u.nombre, ua.nombre,
                    a.id, le.id, f.id, ep.id, es.id, epost.id, s.id;
            """)
            proyectos = cur.fetchall()
        return jsonify(proyectos)
    finally:
        if conn:
            release_db_connection(conn)


@proyectos_bp.route("/proyectos_actividad_reciente", methods=["GET"])
@session_required
def get_proyectos_actividad_reciente(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 'proyecto' as tipo, p.id as proyecto_id, p.nombre as proyecto_nombre,
                    a.nombre as area_nombre, p.monto, p.avance_total_porcentaje,
                    es.nombre as estado_nombre, 'Proyecto actualizado' as descripcion_actividad,
                    p.fecha_actualizacion as fecha
                FROM proyectos p
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE p.fecha_actualizacion IS NOT NULL
                UNION ALL
                SELECT 'documento' as tipo, p.id, p.nombre, a.nombre, p.monto,
                    p.avance_total_porcentaje, es.nombre,
                    'Documento subido' || coalesce(': ' || doc.nombre, ''),
                    doc.fecha_subida
                FROM proyectos_documentos doc
                INNER JOIN proyectos p ON p.id = doc.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE doc.fecha_subida IS NOT NULL
                UNION ALL
                SELECT 'hito' as tipo, p.id, p.nombre, a.nombre, p.monto,
                    p.avance_total_porcentaje, es.nombre,
                    'Hito creado/modificado', h.creado_en
                FROM proyectos_hitos h
                INNER JOIN proyectos p ON p.id = h.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE h.creado_en IS NOT NULL
                UNION ALL
                SELECT 'observacion' as tipo, p.id, p.nombre, a.nombre, p.monto,
                    p.avance_total_porcentaje, es.nombre,
                    'Observación agregada', o.creado_en
                FROM proyectos_observaciones o
                INNER JOIN proyectos p ON p.id = o.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE o.creado_en IS NOT NULL
                UNION ALL
                SELECT 'geomapa' as tipo, p.id, p.nombre, a.nombre, p.monto,
                    p.avance_total_porcentaje, es.nombre,
                    'Geomapa creado/modificado' || coalesce(': ' || g.nombre, ''),
                    g.fecha_creacion
                FROM proyectos_geomapas g
                INNER JOIN proyectos p ON p.id = g.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE g.fecha_creacion IS NOT NULL
                ORDER BY fecha DESC
                LIMIT 20;
            """)
            actividad = cur.fetchall()
        return jsonify(actividad)
    finally:
        if conn:
            release_db_connection(conn)


@proyectos_bp.route("/proyectos", methods=["POST"])
@session_required
def create_proyecto(current_user_id):
    conn = None
    try:
        data = request.get_json()
        ALLOWED_FIELDS = {
            'nombre', 'monto', 'descripcion', 'estado_proyecto_id', 'division_id',
            'foto_url', 'latitud', 'longitud', 'fecha_inicio', 'fecha_termino',
            'presupuesto', 'rut_contratista', 'nombre_contratista', 'avance',
            'codigo_bip', 'etapa_id'
        }
        clean_data = {k: v for k, v in data.items() if k in ALLOWED_FIELDS and v != ""}

        if not data or not data.get("nombre"):
            return jsonify({"message": "El nombre del proyecto es obligatorio"}), 400

        clean_data["user_id"] = current_user_id
        clean_data["actualizado_por"] = current_user_id
        clean_data["fecha_actualizacion"] = datetime.now()

        cols = ", ".join(clean_data.keys())
        placeholders = ", ".join(["%s"] * len(clean_data))

        sql = f"INSERT INTO proyectos ({cols}) VALUES ({placeholders}) RETURNING id"
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, tuple(clean_data.values()))
            new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Proyecto creado", "id": new_id}), 201
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error create_proyecto: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@proyectos_bp.route("/proyectos/<int:pid>", methods=["PUT"])
@session_required
def update_proyecto(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()
        ALLOWED_FIELDS = {
            'nombre', 'monto', 'descripcion', 'estado_proyecto_id', 'division_id',
            'foto_url', 'latitud', 'longitud', 'fecha_inicio', 'fecha_termino',
            'presupuesto', 'rut_contratista', 'nombre_contratista', 'avance',
            'codigo_bip', 'etapa_id'
        }
        clean_data = {k: v for k, v in data.items() if k in ALLOWED_FIELDS}

        if not clean_data:
            return jsonify({"message": "No hay campos para actualizar"}), 400

        clean_data["actualizado_por"] = current_user_id
        fields = []
        values = []

        for k, v in clean_data.items():
            fields.append(f"{k} = %s")
            values.append(v)

        fields.append("fecha_actualizacion = NOW()")
        sql = f"UPDATE proyectos SET {', '.join(fields)} WHERE id = %s"
        values.append(pid)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, tuple(values))
        conn.commit()
        return jsonify({"message": "Proyecto actualizado"})
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error update_proyecto: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@proyectos_bp.route("/proyectos/<int:pid>", methods=["DELETE"])
@session_required
def delete_proyecto(current_user_id, pid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE proyectos
                SET activo = FALSE,
                    actualizado_por = %s,
                    fecha_actualizacion = NOW()
                WHERE id = %s AND activo = TRUE
            """, (current_user_id, pid))

            if cur.rowcount == 0:
                return jsonify({"message": "Proyecto no encontrado o ya desactivado"}), 404
        conn.commit()

        log_control(current_user_id, "eliminar_proyecto", modulo="proyectos",
                    entidad_tipo="proyecto", entidad_id=pid,
                    detalle="Desactivación lógica del proyecto (activo=false)")
        return jsonify({"message": "Proyecto desactivado"})
    finally:
        if conn:
            release_db_connection(conn)


# ─── CATÁLOGOS CRUD ────────────────────────────────────────────

@proyectos_bp.route("/areas", methods=["GET"])
@session_required
def get_areas(current_user_id):
    return crud_simple("areas", current_user_id)

@proyectos_bp.route("/areas", methods=["POST"])
@session_required
def create_area(current_user_id):
    data = request.get_json()
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO areas (nombre) VALUES (%s) RETURNING id", (data["nombre"],))
        new_id = cur.fetchone()[0]
    conn.commit()
    release_db_connection(conn)
    return jsonify({"id": new_id}), 201

@proyectos_bp.route("/areas/<int:id>", methods=["PUT"])
@session_required
def update_area(current_user_id, id):
    data = request.get_json()
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE areas SET nombre = %s, activo = %s WHERE id = %s",
                    (data.get("nombre"), data.get("activo", True), id))
    conn.commit()
    release_db_connection(conn)
    return jsonify({"message": "Actualizado"})

@proyectos_bp.route("/areas/<int:id>", methods=["DELETE"])
@session_required
def delete_area(current_user_id, id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE areas SET activo = FALSE WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"message": "Área desactivada"})
    finally:
        if conn:
            release_db_connection(conn)

# --- Financiamientos ---
@proyectos_bp.route("/financiamientos", methods=["GET"])
@session_required
def get_financiamientos(current_user_id):
    return crud_simple("financiamientos", current_user_id)

@proyectos_bp.route("/financiamientos", methods=["POST"])
@session_required
def create_financiamiento(current_user_id):
    data = request.get_json()
    new_id = generic_create("financiamientos", data, extra_columns=['fuente', 'anyo', 'comentario'])
    return jsonify({"id": new_id}), 201

@proyectos_bp.route("/financiamientos/<int:id>", methods=["PUT"])
@session_required
def update_financiamiento(current_user_id, id):
    data = request.get_json()
    generic_update("financiamientos", id, data, extra_columns=['fuente', 'anyo', 'comentario'])
    return jsonify({"message": "Actualizado"})

@proyectos_bp.route("/financiamientos/<int:id>", methods=["DELETE"])
@session_required
def delete_financiamiento(current_user_id, id):
    generic_delete("financiamientos", id)
    return jsonify({"message": "Financiamiento desactivado"})

# --- Estados Postulación ---
@proyectos_bp.route("/estados_postulacion", methods=["GET"])
@session_required
def get_estados_postulacion(current_user_id):
    return crud_simple("estados_postulacion", current_user_id)

@proyectos_bp.route("/estados_postulacion", methods=["POST"])
@session_required
def create_estado_postulacion(current_user_id):
    data = request.get_json()
    new_id = generic_create("estados_postulacion", data)
    return jsonify({"id": new_id}), 201

@proyectos_bp.route("/estados_postulacion/<int:id>", methods=["PUT"])
@session_required
def update_estado_postulacion(current_user_id, id):
    data = request.get_json()
    generic_update("estados_postulacion", id, data)
    return jsonify({"message": "Actualizado"})

@proyectos_bp.route("/estados_postulacion/<int:id>", methods=["DELETE"])
@session_required
def delete_estado_postulacion(current_user_id, id):
    generic_delete("estados_postulacion", id)
    return jsonify({"message": "Estado desactivado"})

# --- Sectores ---
@proyectos_bp.route("/sectores", methods=["GET"])
@session_required
def get_sectores(current_user_id):
    return crud_simple("sectores", current_user_id)

@proyectos_bp.route("/sectores", methods=["POST"])
@session_required
def create_sector(current_user_id):
    data = request.get_json()
    new_id = generic_create("sectores", data)
    return jsonify({"id": new_id}), 201

@proyectos_bp.route("/sectores/<int:id>", methods=["PUT"])
@session_required
def update_sector(current_user_id, id):
    data = request.get_json()
    generic_update("sectores", id, data)
    return jsonify({"message": "Actualizado"})

@proyectos_bp.route("/sectores/<int:id>", methods=["DELETE"])
@session_required
def delete_sector(current_user_id, id):
    generic_delete("sectores", id)
    return jsonify({"message": "Sector desactivado"})

# --- Lineamientos Estratégicos ---
@proyectos_bp.route("/lineamientos_estrategicos", methods=["GET"])
@session_required
def get_lineamientos(current_user_id):
    return crud_simple("lineamientos_estrategicos", current_user_id)

@proyectos_bp.route("/lineamientos_estrategicos", methods=["POST"])
@session_required
def create_lineamiento(current_user_id):
    data = request.get_json()
    new_id = generic_create("lineamientos_estrategicos", data)
    return jsonify({"id": new_id}), 201

@proyectos_bp.route("/lineamientos_estrategicos/<int:id>", methods=["PUT"])
@session_required
def update_lineamiento(current_user_id, id):
    data = request.get_json()
    generic_update("lineamientos_estrategicos", id, data)
    return jsonify({"message": "Actualizado"})

@proyectos_bp.route("/lineamientos_estrategicos/<int:id>", methods=["DELETE"])
@session_required
def delete_lineamiento(current_user_id, id):
    generic_delete("lineamientos_estrategicos", id)
    return jsonify({"message": "Lineamiento desactivado"})

# --- Etapas Proyecto ---
@proyectos_bp.route("/etapas_proyecto", methods=["GET"])
@session_required
def get_etapas_proyecto(current_user_id):
    return crud_simple("etapas_proyecto", current_user_id)

@proyectos_bp.route("/etapas_proyecto", methods=["POST"])
@session_required
def create_etapa_proyecto(current_user_id):
    data = request.get_json()
    new_id = generic_create("etapas_proyecto", data, extra_columns=['orden'])
    return jsonify({"id": new_id}), 201

@proyectos_bp.route("/etapas_proyecto/<int:id>", methods=["PUT"])
@session_required
def update_etapa_proyecto(current_user_id, id):
    data = request.get_json()
    generic_update("etapas_proyecto", id, data, extra_columns=['orden'])
    return jsonify({"message": "Actualizado"})

@proyectos_bp.route("/etapas_proyecto/<int:id>", methods=["DELETE"])
@session_required
def delete_etapa_proyecto(current_user_id, id):
    generic_delete("etapas_proyecto", id)
    return jsonify({"message": "Etapa desactivada"})

# --- Estados Proyecto ---
@proyectos_bp.route("/estados_proyecto", methods=["GET"])
@session_required
def get_estados_proyecto(current_user_id):
    return crud_simple("estados_proyecto", current_user_id)

@proyectos_bp.route("/estados_proyecto", methods=["POST"])
@session_required
def create_estado_proyecto(current_user_id):
    data = request.get_json()
    new_id = generic_create("estados_proyecto", data, extra_columns=['orden', 'color'])
    return jsonify({"id": new_id}), 201

@proyectos_bp.route("/estados_proyecto/<int:id>", methods=["PUT"])
@session_required
def update_estado_proyecto(current_user_id, id):
    data = request.get_json()
    generic_update("estados_proyecto", id, data, extra_columns=['orden', 'color'])
    return jsonify({"message": "Actualizado"})

@proyectos_bp.route("/estados_proyecto/<int:id>", methods=["DELETE"])
@session_required
def delete_estado_proyecto(current_user_id, id):
    generic_delete("estados_proyecto", id)
    return jsonify({"message": "Estado desactivado"})
