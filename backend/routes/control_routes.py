"""
Blueprint: Módulo de Control – KPIs, Actividad, Resumen, PDF export
Rutas: /control/*
"""
import io
import traceback
from datetime import datetime
import psycopg2.extras
from flask import Blueprint, request, jsonify, send_file

from core.config import logger
from core.database import get_db_connection, release_db_connection
from utils.decorators import session_required
from utils.audit_logger import log_control

control_bp = Blueprint('control', __name__)


@control_bp.route("/control/registrar", methods=["POST"])
@session_required
def control_registrar(current_user_id):
    """Registra acciones de solo-lectura (ver_proyecto, ver_dashboard, etc.)."""
    try:
        data = request.get_json() or {}
        log_control(
            current_user_id,
            data.get("accion", "accion_desconocida")[:80],
            data.get("modulo", "proyectos")[:40],
            entidad_tipo=data.get("entidad_tipo"),
            entidad_id=data.get("entidad_id"),
            entidad_nombre=data.get("entidad_nombre"),
            detalle=data.get("detalle")
        )
        return jsonify({"ok": True}), 201
    except Exception as e:
        logger.error(f"Error en control_registrar: {e}")
        return jsonify({"message": "Error interno"}), 500


@control_bp.route("/control/actividad", methods=["GET"])
@session_required
def control_actividad(current_user_id):
    """Historial completo de actividad de usuarios con filtros y paginación."""
    conn = None
    try:
        conn = get_db_connection()
        filtros, params = [], []

        uid = request.args.get("user_id")
        if uid:
            filtros.append("ca.user_id = %s"); params.append(int(uid))
        accion = request.args.get("accion")
        if accion:
            filtros.append("ca.accion ILIKE %s"); params.append(f"%{accion}%")
        modulo = request.args.get("modulo")
        if modulo:
            filtros.append("ca.modulo = %s"); params.append(modulo)
        fecha_desde = request.args.get("fecha_desde")
        if fecha_desde:
            filtros.append("ca.fecha >= %s"); params.append(fecha_desde)
        fecha_hasta = request.args.get("fecha_hasta")
        if fecha_hasta:
            filtros.append("ca.fecha <= %s"); params.append(fecha_hasta + " 23:59:59")
        entidad_tipo = request.args.get("entidad_tipo")
        if entidad_tipo:
            filtros.append("ca.entidad_tipo = %s"); params.append(entidad_tipo)
        entidad_id = request.args.get("entidad_id")
        if entidad_id:
            filtros.append("ca.entidad_id = %s"); params.append(int(entidad_id))
        q = request.args.get("q")
        if q:
            filtros.append("(ca.detalle ILIKE %s OR ca.entidad_nombre ILIKE %s OR u.nombre ILIKE %s)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]

        where_clause = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(10, int(request.args.get("per_page", 50))))
        offset = (page - 1) * per_page

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                SELECT COUNT(*) AS total
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                {where_clause}
            """, params)
            total = cur.fetchone()["total"]

            cur.execute(f"""
                SELECT ca.id, ca.user_id, u.nombre AS nombre_usuario, u.email,
                       ca.accion, ca.modulo, ca.entidad_tipo, ca.entidad_id,
                       ca.entidad_nombre, ca.exitoso, ca.detalle,
                       ca.ip_origen::TEXT, ca.endpoint, ca.fecha
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                {where_clause}
                ORDER BY ca.fecha DESC LIMIT %s OFFSET %s
            """, params + [per_page, offset])
            rows = cur.fetchall()

        return jsonify({
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page, "data": rows
        })
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en control_actividad: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@control_bp.route("/control/actividad/proyecto/<int:proyecto_id>", methods=["GET"])
@session_required
def control_actividad_proyecto(current_user_id, proyecto_id):
    """Historial completo de un proyecto específico."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT ca.id, ca.accion, ca.modulo, ca.user_id,
                       u.nombre AS nombre_usuario, u.email,
                       ca.exitoso, ca.detalle, ca.ip_origen::TEXT,
                       ca.endpoint, ca.fecha
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                WHERE ca.entidad_tipo = 'proyecto' AND ca.entidad_id = %s
                ORDER BY ca.fecha DESC LIMIT 500
            """, (proyecto_id,))
            rows = cur.fetchall()

            cur.execute("SELECT id, nombre FROM proyectos WHERE id = %s", (proyecto_id,))
            proyecto = cur.fetchone()

        return jsonify({"proyecto": proyecto, "actividad": rows})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en control_actividad_proyecto: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@control_bp.route("/control/actividad/usuario/<int:uid>", methods=["GET"])
@session_required
def control_actividad_usuario(current_user_id, uid):
    """Historial completo de un usuario específico."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT ca.id, ca.accion, ca.modulo,
                       ca.entidad_tipo, ca.entidad_id, ca.entidad_nombre,
                       ca.exitoso, ca.detalle, ca.ip_origen::TEXT,
                       ca.endpoint, ca.fecha
                FROM control_actividad ca WHERE ca.user_id = %s
                ORDER BY ca.fecha DESC LIMIT 1000
            """, (uid,))
            actividad = cur.fetchall()

            cur.execute("""
                SELECT user_id, nombre, email, nivel_acceso
                FROM users WHERE user_id = %s
            """, (uid,))
            usuario = cur.fetchone()

        if usuario is None:
            usuario = {"user_id": uid, "nombre": f"Usuario #{uid}", "email": "", "nivel_acceso": None}
        return jsonify({"usuario": usuario, "actividad": actividad})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en control_actividad_usuario: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@control_bp.route("/control/kpi", methods=["GET"])
@session_required
def control_kpi(current_user_id):
    """KPIs globales del módulo de control."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT COUNT(*) AS total_acciones,
                       COUNT(DISTINCT user_id) AS usuarios_activos,
                       COUNT(DISTINCT entidad_id) FILTER (WHERE entidad_tipo = 'proyecto') AS proyectos_accedidos,
                       COUNT(*) FILTER (WHERE exitoso = FALSE) AS acciones_fallidas,
                       COUNT(*) FILTER (WHERE fecha >= NOW() - INTERVAL '24 hours') AS acciones_hoy,
                       COUNT(*) FILTER (WHERE fecha >= NOW() - INTERVAL '7 days') AS acciones_semana,
                       COUNT(DISTINCT user_id) FILTER (WHERE fecha >= NOW() - INTERVAL '7 days') AS usuarios_semana
                FROM control_actividad
            """)
            totales = cur.fetchone()

            cur.execute("SELECT modulo, COUNT(*) AS total FROM control_actividad GROUP BY modulo ORDER BY total DESC")
            por_modulo = cur.fetchall()

            cur.execute("SELECT accion, COUNT(*) AS total FROM control_actividad GROUP BY accion ORDER BY total DESC LIMIT 10")
            top_acciones = cur.fetchall()

            cur.execute("""
                SELECT DATE(fecha AT TIME ZONE 'America/Santiago') AS dia, COUNT(*) AS total
                FROM control_actividad WHERE fecha >= NOW() - INTERVAL '30 days'
                GROUP BY dia ORDER BY dia ASC
            """)
            actividad_diaria = cur.fetchall()

            cur.execute("""
                SELECT ca.user_id, u.nombre, u.email, COUNT(*) AS total_acciones, MAX(ca.fecha) AS ultima_actividad
                FROM control_actividad ca LEFT JOIN users u ON u.user_id = ca.user_id
                GROUP BY ca.user_id, u.nombre, u.email ORDER BY total_acciones DESC LIMIT 10
            """)
            top_usuarios = cur.fetchall()

            cur.execute("""
                SELECT ca.entidad_id AS proyecto_id, ca.entidad_nombre AS nombre_proyecto,
                       COUNT(*) AS total_accesos, COUNT(DISTINCT ca.user_id) AS usuarios_distintos,
                       MAX(ca.fecha) AS ultimo_acceso
                FROM control_actividad ca
                WHERE ca.entidad_tipo = 'proyecto' AND ca.entidad_id IS NOT NULL
                GROUP BY ca.entidad_id, ca.entidad_nombre ORDER BY total_accesos DESC LIMIT 10
            """)
            top_proyectos = cur.fetchall()

            cur.execute("""
                SELECT ca.id, ca.accion, ca.modulo, ca.user_id, u.nombre AS nombre_usuario,
                       ca.entidad_tipo, ca.entidad_nombre, ca.exitoso, ca.detalle,
                       ca.ip_origen::TEXT, ca.fecha
                FROM control_actividad ca LEFT JOIN users u ON u.user_id = ca.user_id
                ORDER BY ca.fecha DESC LIMIT 20
            """)
            ultimas_acciones = cur.fetchall()

            cur.execute("""
                SELECT EXTRACT(HOUR FROM fecha AT TIME ZONE 'America/Santiago')::INT AS hora, COUNT(*) AS total
                FROM control_actividad WHERE fecha >= NOW() - INTERVAL '30 days'
                GROUP BY hora ORDER BY hora ASC
            """)
            por_hora = cur.fetchall()

        return jsonify({
            "totales": totales, "por_modulo": por_modulo, "top_acciones": top_acciones,
            "actividad_diaria": actividad_diaria, "top_usuarios": top_usuarios,
            "top_proyectos": top_proyectos, "ultimas_acciones": ultimas_acciones,
            "por_hora": por_hora
        })
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en control_kpi: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@control_bp.route("/control/resumen_usuarios", methods=["GET"])
@session_required
def control_resumen_usuarios(current_user_id):
    """Tabla resumen de KPIs por usuario."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT u.user_id, u.nombre AS nombre_usuario, u.email, u.nivel_acceso, u.activo,
                       COUNT(ca.id) AS total_acciones,
                       COUNT(ca.id) FILTER (WHERE ca.accion = 'ver_proyecto') AS vistas_proyecto,
                       COUNT(ca.id) FILTER (WHERE ca.accion = 'editar_proyecto') AS ediciones_proyecto,
                       COUNT(ca.id) FILTER (WHERE ca.exitoso = FALSE) AS acciones_fallidas,
                       MAX(ca.fecha) AS ultima_actividad
                FROM users u
                LEFT JOIN control_actividad ca ON ca.user_id = u.user_id
                WHERE u.activo = TRUE
                GROUP BY u.user_id ORDER BY total_acciones DESC, u.nombre ASC
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en control_resumen_usuarios: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@control_bp.route("/control/refresh_stats", methods=["POST"])
@session_required
def control_refresh_stats(current_user_id):
    """Refresca las vistas materializadas de estadísticas."""
    conn = None
    try:
        conn = get_db_connection()

        for view_name in ["control_resumen_usuario", "control_resumen_proyecto"]:
            try:
                with conn.cursor() as cur:
                    cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                conn.commit()
            except Exception as e1:
                conn.rollback()
                logger.warning(f"CONCURRENT falló para {view_name} ({e1}), usando modo normal")
                with conn.cursor() as cur:
                    cur.execute(f"REFRESH MATERIALIZED VIEW {view_name}")
                conn.commit()

        log_control(current_user_id, "refresh_stats_control", modulo="control",
                    detalle="Vistas materializadas refrescadas")
        return jsonify({"ok": True, "mensaje": "Estadísticas actualizadas"})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en refresh_stats: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)


@control_bp.route("/control/export_pdf", methods=["GET"])
@session_required
def control_export_pdf(current_user_id):
    """Genera un PDF ejecutivo con los KPIs del módulo de control."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT COUNT(*) AS total_acciones, COUNT(DISTINCT user_id) AS usuarios_activos,
                       COUNT(DISTINCT entidad_id) FILTER (WHERE entidad_tipo='proyecto') AS proyectos_accedidos,
                       COUNT(*) FILTER (WHERE exitoso = FALSE) AS acciones_fallidas,
                       COUNT(*) FILTER (WHERE fecha >= NOW() - INTERVAL '24 hours') AS acciones_hoy,
                       COUNT(*) FILTER (WHERE fecha >= NOW() - INTERVAL '7 days') AS acciones_semana
                FROM control_actividad
            """)
            totales = dict(cur.fetchone())

            cur.execute("""
                SELECT ca.user_id, u.nombre, COUNT(*) AS total
                FROM control_actividad ca LEFT JOIN users u ON u.user_id = ca.user_id
                GROUP BY ca.user_id, u.nombre ORDER BY total DESC LIMIT 10
            """)
            top_usuarios = cur.fetchall()

            cur.execute("""
                SELECT entidad_id, entidad_nombre, COUNT(*) AS total
                FROM control_actividad WHERE entidad_tipo='proyecto' AND entidad_id IS NOT NULL
                GROUP BY entidad_id, entidad_nombre ORDER BY total DESC LIMIT 10
            """)
            top_proyectos = cur.fetchall()

            cur.execute("""
                SELECT accion, COUNT(*) AS total
                FROM control_actividad GROUP BY accion ORDER BY total DESC LIMIT 10
            """)
            top_acciones = cur.fetchall()

        # Intentar generar PDF con reportlab
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            story = []

            title_style = ParagraphStyle('title_ctrl', parent=styles['Heading1'],
                fontSize=18, textColor=colors.HexColor('#4f46e5'), spaceAfter=6, alignment=TA_CENTER)
            sub_style = ParagraphStyle('sub_ctrl', parent=styles['Normal'],
                fontSize=10, textColor=colors.grey, spaceAfter=16, alignment=TA_CENTER)
            h2_style = ParagraphStyle('h2_ctrl', parent=styles['Heading2'],
                fontSize=13, textColor=colors.HexColor('#1e293b'), spaceBefore=16, spaceAfter=8)

            now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            story.append(Paragraph("📊 MÓDULO DE CONTROL – INFORME EJECUTIVO", title_style))
            story.append(Paragraph(f"Generado: {now_str}", sub_style))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#4f46e5')))
            story.append(Spacer(1, 0.4*cm))

            # KPI table
            story.append(Paragraph("1. KPI Globales del Sistema", h2_style))
            kpi_data = [["Indicador", "Valor"]]
            for label, key in [("Total Acciones", "total_acciones"), ("Usuarios Activos", "usuarios_activos"),
                               ("Proyectos Accedidos", "proyectos_accedidos"), ("Acciones Fallidas", "acciones_fallidas"),
                               ("Acciones Hoy", "acciones_hoy"), ("Acciones Semana", "acciones_semana")]:
                kpi_data.append([label, str(totales.get(key, 0))])
            t = Table(kpi_data, colWidths=[10*cm, 5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))

            # Top usuarios
            story.append(Paragraph("2. Top 10 Usuarios Más Activos", h2_style))
            u_data = [["#", "Usuario", "Total"]]
            for i, row in enumerate(top_usuarios, 1):
                u_data.append([str(i), row.get("nombre", "—"), str(row.get("total", 0))])
            t2 = Table(u_data, colWidths=[1*cm, 10*cm, 4*cm])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(t2)

            doc.build(story)
            buf.seek(0)
            log_control(current_user_id, "exportar_pdf", modulo="control", detalle="PDF exportado")
            return send_file(buf, mimetype="application/pdf", as_attachment=True,
                             download_name=f"informe_control_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")

        except ImportError:
            log_control(current_user_id, "exportar_pdf_fallback", modulo="control",
                        detalle="reportlab no disponible")
            return jsonify({
                "advertencia": "reportlab no instalado – datos en JSON",
                "totales": totales, "top_usuarios": top_usuarios,
                "top_proyectos": top_proyectos, "top_acciones": top_acciones
            })
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        logger.error(f"Error en control_export_pdf: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)
