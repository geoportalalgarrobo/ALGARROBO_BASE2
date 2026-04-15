"""
Blueprint: Auditoría Integral – Lanzar, Estado, Reportes, PDF, Envío, Dashboard
Rutas: /auditoria/*
"""
import os
import re
import traceback
import psycopg2.extras
from flask import Blueprint, request, jsonify, send_file

from core.config import logger, AUDIT_OUT_DIR
from core.database import get_db_connection, release_db_connection
from utils.decorators import session_required
from utils.audit_logger import log_control

auditoria_bp = Blueprint('auditoria_integral', __name__)


def get_auditoria_engine():
    try:
        import auditoria_engine
        return auditoria_engine
    except ImportError as e:
        logger.error(f"Error cargando motor de auditoría: {e}")
        return None


def get_auditoria_catalogos(cur, area_id=None, etapa_id=None, estado_id=None):
    """Auxiliar para catálogos en cascada del módulo de auditoría."""
    cur.execute("""
        SELECT DISTINCT a.id, a.nombre
        FROM areas a JOIN proyectos p ON p.area_id = a.id ORDER BY a.nombre
    """)
    areas = cur.fetchall()

    sql = "SELECT DISTINCT ep.id, ep.nombre FROM etapas_proyecto ep JOIN proyectos p ON p.etapa_proyecto_id = ep.id WHERE 1=1"
    params = []
    if area_id:
        sql += " AND p.area_id = %s"; params.append(int(area_id))
    sql += " ORDER BY ep.nombre"
    cur.execute(sql, params)
    etapas = cur.fetchall()

    sql = "SELECT DISTINCT es.id, es.nombre FROM estados_proyecto es JOIN proyectos p ON p.estado_proyecto_id = es.id WHERE 1=1"
    params = []
    if area_id:
        sql += " AND p.area_id = %s"; params.append(int(area_id))
    if etapa_id:
        sql += " AND p.etapa_proyecto_id = %s"; params.append(int(etapa_id))
    sql += " ORDER BY es.nombre"
    cur.execute(sql, params)
    estados = cur.fetchall()

    sql = "SELECT DISTINCT p.profesional_1 FROM proyectos p WHERE p.profesional_1 IS NOT NULL"
    params = []
    if area_id:
        sql += " AND p.area_id = %s"; params.append(int(area_id))
    if etapa_id:
        sql += " AND p.etapa_proyecto_id = %s"; params.append(int(etapa_id))
    if estado_id:
        sql += " AND p.estado_proyecto_id = %s"; params.append(int(estado_id))
    sql += " ORDER BY 1"
    cur.execute(sql, params)
    profesionales = [r["profesional_1"] for r in cur.fetchall()]

    return {
        "areas": [dict(r) for r in areas],
        "etapas": [dict(r) for r in etapas],
        "estados": [dict(r) for r in estados],
        "profesionales": profesionales
    }


@auditoria_bp.route("/auditoria/lanzar", methods=["POST"])
@session_required
def auditoria_lanzar(current_user_id):
    """Lanza la auditoría integral de todos los proyectos (async)."""
    engine = get_auditoria_engine()
    if not engine:
        return jsonify({"ok": False, "message": "Motor de auditoría no disponible"}), 503

    ejecutor_nombre = f"ID: {current_user_id}"
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM users WHERE user_id = %s", (current_user_id,))
            user_row = cur.fetchone()
            if user_row:
                ejecutor_nombre = user_row[0]
    except Exception as e:
        logger.warning(f"Error obteniendo nombre de ejecutor: {e}")
    finally:
        if conn: release_db_connection(conn)

    base_url = request.json.get("base_url", "https://geoportalalgarrobo.github.io/ALGARROBO_BASE2") \
        if request.is_json else "https://geoportalalgarrobo.github.io/ALGARROBO_BASE2"

    lanzado = engine.run_auditoria_async(
        db_factory=get_db_connection,
        release_fn=release_db_connection,
        ejecutor_nombre=ejecutor_nombre,
        base_url=base_url,
    )
    if not lanzado:
        return jsonify({"ok": False, "message": "Ya hay una auditoría en curso"}), 409

    log_control(current_user_id, "lanzar_auditoria", modulo="auditoria",
                detalle="Auditoría integral iniciada")
    return jsonify({"ok": True, "message": "Auditoría iniciada en segundo plano"})


@auditoria_bp.route("/auditoria/estado", methods=["GET"])
@session_required
def auditoria_estado(current_user_id):
    """Retorna el estado en tiempo real de la auditoría en curso."""
    engine = get_auditoria_engine()
    if not engine:
        return jsonify({"error": "No disponible"}), 503
    return jsonify(engine.get_status())


@auditoria_bp.route("/auditoria/reportes", methods=["GET"])
@session_required
def auditoria_reportes(current_user_id):
    """Lista los PDFs disponibles enriquecidos con datos de BD."""
    conn = None
    try:
        pdf_qual, pdf_hist = set(), set()
        if os.path.exists(AUDIT_OUT_DIR):
            for fn in os.listdir(AUDIT_OUT_DIR):
                if fn.endswith(".pdf"):
                    if fn.startswith("Auditoria_Proyecto_"):
                        pid_str = fn.replace("Auditoria_Proyecto_", "").replace(".pdf", "")
                        pdf_qual.add(int(pid_str))
                    elif fn.startswith("Historial_Cambios_Proyecto_"):
                        pid_str = fn.replace("Historial_Cambios_Proyecto_", "").replace(".pdf", "")
                        pdf_hist.add(int(pid_str))
                    elif fn.endswith("_cambios.pdf"):
                        pid_str = fn.replace("_cambios.pdf", "")
                        pdf_hist.add(int(pid_str))
                    elif fn.replace(".pdf", "").isdigit():
                        pdf_qual.add(int(fn.replace(".pdf", "")))

        all_ids = list(pdf_qual | pdf_hist)

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            catalogos = get_auditoria_catalogos(cur)
            if not all_ids:
                return jsonify({"reportes": [], "total": 0, "catalogos": catalogos})

            cur.execute("""
                SELECT p.id, p.nombre, p.area_id, p.etapa_proyecto_id, p.estado_proyecto_id, p.profesional_1,
                       a.nombre AS area_nombre, et.nombre AS etapa_nombre, es.nombre AS estado_nombre
                FROM proyectos p
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN etapas_proyecto et ON et.id = p.etapa_proyecto_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE p.id = ANY(%s) ORDER BY p.nombre
            """, (all_ids,))
            proyectos_data = {proy["id"]: dict(proy) for proy in cur.fetchall()}

            cur.execute("""
                SELECT projeto_id AS id, puntaje_general, alertas_criticas, fecha_ejecucion
                FROM (
                    SELECT ap.proyecto_id AS projeto_id, ap.puntaje_general, ap.alertas_criticas, al.fecha_ejecucion,
                           ROW_NUMBER() OVER(PARTITION BY ap.proyecto_id ORDER BY al.fecha_ejecucion DESC) as rn
                    FROM auditoria_proyectos ap JOIN auditoria_lotes al ON al.id = ap.lote_id
                ) sub WHERE rn = 1 AND projeto_id = ANY(%s)
            """, (all_ids,))
            audit_data = {r["id"]: dict(r) for r in cur.fetchall()}

        reportes = []
        for pid in all_ids:
            if pid not in proyectos_data:
                continue
            proy = proyectos_data[pid]
            aud = audit_data.get(pid, {})
            reportes.append({
                "proyecto_id": pid, "nombre": proy["nombre"],
                "area_id": proy["area_id"], "etapa_id": proy["etapa_proyecto_id"],
                "estado_id": proy["estado_proyecto_id"],
                "area_nombre": proy["area_nombre"], "etapa_nombre": proy["etapa_nombre"],
                "estado_nombre": proy["estado_nombre"], "profesional_1": proy["profesional_1"],
                "puntaje_general": float(aud.get("puntaje_general") or 0),
                "alertas_criticas": int(aud.get("alertas_criticas") or 0),
                "has_calidad": pid in pdf_qual, "has_cambios": pid in pdf_hist,
                "fecha_auditoria": aud.get("fecha_ejecucion").isoformat() if aud.get("fecha_ejecucion") else None
            })

        return jsonify({"reportes": reportes, "total": len(reportes), "catalogos": catalogos})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error auditoria_reportes: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@auditoria_bp.route("/auditoria/pdf/<int:proyecto_id>", methods=["GET"])
@session_required
def auditoria_pdf_view(current_user_id, proyecto_id):
    """Sirve el PDF de auditoría de un proyecto."""
    tipo = request.args.get("tipo", "calidad")
    if tipo == "cambios":
        filename = f"Historial_Cambios_Proyecto_{proyecto_id}.pdf"
    else:
        filename = f"Auditoria_Proyecto_{proyecto_id}.pdf"

    pdf_path = os.path.join(AUDIT_OUT_DIR, filename)

    if not os.path.exists(pdf_path):
        alt = f"{proyecto_id}_cambios.pdf" if tipo == "cambios" else f"{proyecto_id}.pdf"
        alt_path = os.path.join(AUDIT_OUT_DIR, alt)
        if os.path.exists(alt_path):
            pdf_path = alt_path

    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF no encontrado. Ejecute la auditoría primero."}), 404

    as_attachment = request.args.get("download", "0") == "1"
    download_name = f"auditoria_{proyecto_id}.pdf"

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM proyectos WHERE id = %s", (proyecto_id,))
            row = cur.fetchone()
            if row:
                safe_name = re.sub(r'[^\w\s-]', '', row[0] or '').strip()[:50]
                download_name = f"auditoria_{safe_name}_{proyecto_id}.pdf"
    except Exception:
        pass
    finally:
        if conn: release_db_connection(conn)

    log_control(current_user_id, "ver_pdf_auditoria", modulo="auditoria",
                entidad_tipo="proyecto", entidad_id=proyecto_id,
                detalle=f"PDF auditoria proyecto {proyecto_id}")
    return send_file(pdf_path, mimetype="application/pdf",
                     download_name=download_name, as_attachment=as_attachment)


@auditoria_bp.route("/proyectos/<int:proyecto_id>/enviar-auditoria", methods=["POST"])
@session_required
def endpoint_enviar_auditoria(current_user_id, proyecto_id):
    """Envía el reporte de auditoría por correo a los responsables."""
    import correo

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT nombre, profesional_1, profesional_2, profesional_3, profesional_4, profesional_5
                FROM proyectos WHERE id = %s
            """, (proyecto_id,))
            proyecto = cur.fetchone()

        if not proyecto:
            return jsonify({"success": False, "message": "Proyecto no encontrado"}), 404

        responsables = [proyecto[f'profesional_{i}'] for i in range(1, 6)]

        filename = f"Auditoria_Proyecto_{proyecto_id}.pdf"
        pdf_path = os.path.join(AUDIT_OUT_DIR, filename)
        if not os.path.exists(pdf_path):
            alt_path = os.path.join(AUDIT_OUT_DIR, f"{proyecto_id}.pdf")
            if os.path.exists(alt_path):
                pdf_path = alt_path

        if not os.path.exists(pdf_path):
            return jsonify({"success": False, "message": "No se encontró el reporte. Ejecute la auditoría primero."}), 404

        resultado = correo.enviar_email_responsables(
            proyecto_id=proyecto_id, responsables_names=responsables,
            ruta_pdf=pdf_path, proyecto_nombre=proyecto['nombre']
        )

        if resultado["success"]:
            log_control(current_user_id, "enviar_auditoria_email", modulo="auditoria",
                        entidad_tipo="proyecto", entidad_id=proyecto_id,
                        detalle=f"Enviado a: {', '.join(resultado['enviados'])}")
            return jsonify(resultado), 200
        return jsonify(resultado), 400
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en endpoint_enviar_auditoria: {e}")
        return jsonify({"success": False, "message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@auditoria_bp.route("/auditoria/enviar-lote", methods=["POST"])
@session_required
def endpoint_enviar_auditoria_lote(current_user_id):
    """Envía las auditorías de todos los proyectos en lote."""
    import correo

    if not os.path.exists(AUDIT_OUT_DIR):
        return jsonify({"success": False, "message": "No se encontraron reportes."}), 404

    files = [f for f in os.listdir(AUDIT_OUT_DIR)
             if f.startswith("Auditoria_Proyecto_") and f.endswith(".pdf")]
    if not files:
        return jsonify({"success": False, "message": "No hay reportes generados."}), 404

    project_files = {}
    for f in files:
        try:
            pid = int(f.replace("Auditoria_Proyecto_", "").replace(".pdf", ""))
            project_files[pid] = f
        except:
            continue

    pids = list(project_files.keys())
    conn = None
    enviados_count, errores, skipped = 0, [], 0

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT id, nombre, profesional_1, profesional_2, profesional_3, profesional_4, profesional_5
                FROM proyectos WHERE id = ANY(%s)
            """, (pids,))
            proyectos = cur.fetchall()

        for p in proyectos:
            pid = p['id']
            pdf_path = os.path.join(AUDIT_OUT_DIR, project_files[pid])
            responsables = [p[f'profesional_{i}'] for i in range(1, 6)]

            res = correo.enviar_email_responsables(
                proyecto_id=pid, responsables_names=responsables,
                ruta_pdf=pdf_path, proyecto_nombre=p['nombre']
            )

            if res["success"]:
                enviados_count += 1
                log_control(current_user_id, "enviar_auditoria_email_lote", modulo="auditoria",
                            entidad_tipo="proyecto", entidad_id=pid,
                            detalle=f"Enviado a: {', '.join(res['enviados'])}")
            elif "No se encontraron correos" in res["message"]:
                skipped += 1
            else:
                errores.append(f"Proyecto {pid}: {res['message']}")

        msg = f"Enviados: {enviados_count}."
        if skipped > 0: msg += f" Ignorados: {skipped}."
        if errores: msg += f" Errores: {len(errores)}."

        return jsonify({
            "success": True, "message": msg,
            "detalles": {"enviados": enviados_count, "errores": errores, "skipped": skipped}
        })
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en enviar_auditoria_lote: {e}")
        return jsonify({"success": False, "message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@auditoria_bp.route("/auditoria/dashboard", methods=["GET"])
@session_required
def auditoria_dashboard(current_user_id):
    """KPIs cruzados de auditoría."""
    conn = None
    try:
        conn = get_db_connection()
        lote_id_f = request.args.get("lote_id")
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if lote_id_f:
                target_lote_id = int(lote_id_f)
            else:
                cur.execute("SELECT MAX(lote_id) FROM auditoria_proyectos")
                target_lote_id = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT id, fecha_ejecucion, total_proyectos_auditados,
                       ROUND(promedio_calidad_general::NUMERIC, 1) AS promedio, usuario_ejecutor
                FROM auditoria_lotes ORDER BY fecha_ejecucion DESC LIMIT 20
            """)
            lotes = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT ap.proyecto_id AS id, p.nombre, p.area_id, p.etapa_proyecto_id, p.estado_proyecto_id,
                       p.profesional_1, a.nombre AS area_nombre, et.nombre AS etapa_nombre, es.nombre AS estado_nombre,
                       ap.puntaje_general, ap.alertas_criticas, ap.alertas_altas, ap.alertas_medias, ap.alertas_bajas,
                       ap.cant_proximos_pasos, ap.cant_documentos, ap.avance_declarado, ap.etapa
                FROM auditoria_proyectos ap
                JOIN proyectos p ON p.id = ap.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN etapas_proyecto et ON et.id = p.etapa_proyecto_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE ap.lote_id = %s
            """, (target_lote_id,))
            proyectos = [dict(r) for r in cur.fetchall()]

            ctrl_filtros, ctrl_params = ["1=1"], []
            if fecha_desde:
                ctrl_filtros.append("ca.fecha >= %s"); ctrl_params.append(fecha_desde)
            if fecha_hasta:
                ctrl_filtros.append("ca.fecha <= %s"); ctrl_params.append(fecha_hasta + " 23:59:59")

            cur.execute(f"""
                SELECT COUNT(*) AS total_acciones,
                       COUNT(*) FILTER (WHERE ca.fecha >= NOW() - INTERVAL '24 hours') AS hoy,
                       COUNT(DISTINCT ca.user_id) AS usuarios_activos,
                       COUNT(*) FILTER (WHERE ca.exitoso = FALSE) AS fallidas
                FROM control_actividad ca WHERE {" AND ".join(ctrl_filtros)}
            """, ctrl_params)
            ctrl_kpi = dict(cur.fetchone() or {})

            cur.execute("""
                SELECT al.fecha_ejecucion AS fecha, ROUND(AVG(ap.puntaje_general)::NUMERIC, 1) AS puntaje_prom
                FROM auditoria_proyectos ap JOIN auditoria_lotes al ON al.id = ap.lote_id
                GROUP BY al.id, al.fecha_ejecucion ORDER BY al.fecha_ejecucion ASC LIMIT 15
            """)
            evolucion = [dict(r) for r in cur.fetchall()]

            catalogos = get_auditoria_catalogos(cur)

        return jsonify({
            "target_lote_id": target_lote_id, "lotes": lotes,
            "proyectos": proyectos, "ctrl_kpi": ctrl_kpi,
            "evolucion": evolucion, "catalogos": catalogos
        })
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error auditoria_dashboard: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)
