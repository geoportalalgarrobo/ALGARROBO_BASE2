import os
import hashlib

# ── HACK: Parche de compatibilidad para hashlib ────────────────────────────────
_orig_new = hashlib.new
def _patched_new(name, *args, **kwargs):
    kwargs.pop('usedforsecurity', None)
    kwargs.pop('useforsecurity', None)
    return _orig_new(name, *args, **kwargs)
hashlib.new = _patched_new

try:
    _orig_md5 = hashlib.md5
    def _patched_md5(*args, **kwargs):
        kwargs.pop('usedforsecurity', None)
        kwargs.pop('useforsecurity', None)
        return _orig_md5(*args, **kwargs)
    hashlib.md5 = _patched_md5
except: pass
# ───────────────────────────────────────────────────────────────────────────────

import re
import json
import logging
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
AUDIT_OUT_DIR  = os.path.join(BASE_DIR, "auditoria_reportes")   # sólo 1 ejecución guardada
os.makedirs(AUDIT_OUT_DIR, exist_ok=True)

# Estado global de la tarea asíncrona (1 ejecución a la vez)
_task_lock   = threading.Lock()
_task_status = {
    "running"    : False,
    "lote_id"    : None,
    "total"      : 0,
    "procesados" : 0,
    "errores"    : 0,
    "iniciado_en": None,
    "finalizado_en": None,
    "ejecutado_por": None,  # user_id
    "error_fatal": None,
}


def get_status() -> dict:
    """Retorna copia del estado actual."""
    with _task_lock:
        return dict(_task_status)


def _update_status(**kwargs):
    with _task_lock:
        _task_status.update(kwargs)


# ──────────────────────────────────────────────
# HELPERS PDF
# ──────────────────────────────────────────────
def _generate_pdf(lines: list, filepath: str) -> bool:
    """Genera PDF desde lista de strings (igual que verificador.py)."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER

        # Extraemos el ID o nombre base del archivo para el título
        nombre_base = os.path.basename(filepath).replace(".pdf", "").replace("_", " ")

        doc    = SimpleDocTemplate(filepath, pagesize=landscape(A4),
                                   leftMargin=1.5*cm, rightMargin=1.5*cm,
                                   topMargin=1.5*cm, bottomMargin=1.5*cm,
                                   # METADATOS ANTI-SPAM
                                   title=f"Reporte de Auditoría - {nombre_base}",
                                   author="Departamento de Planificación - Algarrobo",
                                   subject="Control de Calidad y Seguimiento de Obras",
                                   creator="Sistema de Gestión Geoportal Algarrobo")
        styles = getSampleStyleSheet()
        story  = []

        title_style  = ParagraphStyle('t', parent=styles['Heading1'], fontSize=18,
                                      textColor=colors.HexColor('#4f46e5'),
                                      spaceAfter=10, alignment=TA_CENTER)
        sub_style    = ParagraphStyle('s', parent=styles['Normal'],   fontSize=12,
                                      textColor=colors.grey, spaceAfter=18, alignment=TA_CENTER)
        h2_style     = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=14,
                                      textColor=colors.HexColor('#1e293b'),
                                      spaceBefore=14, spaceAfter=8)
        body_style   = ParagraphStyle('b', parent=styles['Normal'], fontSize=10, leading=14)
        bold_style   = ParagraphStyle('bb', parent=body_style, fontName='Helvetica-Bold')

        cur_table = []

        def commit_table():
            if not cur_table:
                return
            fmt = []
            for ri, row in enumerate(cur_table):
                frow = []
                for cell in row:
                    if ri == 0:
                        frow.append(cell)
                    else:
                        raw = str(cell).strip()
                        raw = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        if "[" in raw and "](" in raw:
                            raw = re.sub(r'\[(.*?)\]\((.*?)\)',
                                         r'<a href="\2" color="blue"><u>\1</u></a>', raw)
                        st = bold_style if ("CRÍTICO" in raw or "🔴" in raw) else body_style
                        frow.append(Paragraph(raw, st))
                fmt.append(frow)

            cols = len(cur_table[0])
            hdr  = " ".join(cur_table[0]).upper()
            
            # Mapa de anchos expandido para cubrir Verificador 1 y 2
            wmap = {
                2: [5*cm, 22*cm],
                3: [5*cm, 5*cm, 17*cm],
                4: [5*cm, 5*cm, 6*cm, 11*cm],
                5: [4.5*cm, 3.5*cm, 4*cm, 4*cm, 11*cm],
                6: [2.8*cm, 3.5*cm, 3.5*cm, 3*cm, 3*cm, 11.2*cm]
            }
            cw = wmap.get(cols)
            if cols == 7:
                cw = [2*cm, 10*cm, 3*cm, 2*cm, 2*cm, 3.5*cm, 3.5*cm]
            
            hbg = colors.HexColor('#4f46e5') # Indigo default
            if any(x in hdr for x in ["NIVEL", "CÓDIGO", "CRÍTICA", "ALERTA"]):
                hbg = colors.HexColor('#ef4444') # Rojo
            elif "PUNTAJE" in hdr or "AVANCE" in hdr:
                hbg = colors.HexColor('#10b981') # Verde
            elif any(x in hdr for x in ["ACCIÓN", "PRIORIDAD", "HISTORIAL", "CAMBIOS"]):
                hbg = colors.HexColor('#f59e0b') # Ambar
            elif any(x in hdr for x in ["FECHA", "AUTOR"]):
                hbg = colors.HexColor('#3b82f6') # Azul

            t = Table(fmt, colWidths=cw)
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0), hbg),
                ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
                ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',      (0, 0), (-1, -1), 10),
                ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
                ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.4*cm))
            cur_table.clear()

        for line in lines:
            orig = line
            line = line.strip()
            if not line or set(line).issubset({'_','═','─','┌','┐','└','┘','│','█','░','|'}) \
                    or "0%        25%" in line:
                commit_table()
                continue
            if '\t' in orig:
                cur_table.append([c.strip() for c in orig.split('\t')])
            else:
                commit_table()
                if line.startswith("📋"):
                    story.append(Paragraph(line, title_style))
                elif "Sistema Multi-Dimensional" in line:
                    story.append(Paragraph(line, sub_style))
                elif line[:2] in ("📊","🎯","🚨","📈","✅","🔍","🕒","📋"):
                    story.append(Paragraph(line, h2_style))
                    story.append(HRFlowable(width="100%", thickness=1.5,
                                            color=colors.HexColor('#4f46e5')))
                    story.append(Spacer(1, 0.2*cm))
                elif "CALIDAD GENERAL:" in line:
                    sc = ParagraphStyle('sc', parent=body_style, fontSize=14,
                                        fontName='Helvetica-Bold',
                                        textColor=colors.HexColor('#ef4444') if "⚠️" in line
                                        else colors.HexColor('#10b981'))
                    story.append(Paragraph(line, sc))
                    story.append(Spacer(1, 0.3*cm))
                elif "BARRA DE CALIDAD" not in line:
                    story.append(Paragraph(line, body_style))
                    story.append(Spacer(1, 0.1*cm))

        commit_table()
        doc.build(story)
        return True
    except Exception as e:
        logger.error(f"PDF error {filepath}: {e}")
        return False


# ──────────────────────────────────────────────
# MOTOR DE AUDITORÍA INDIVIDUAL
# ──────────────────────────────────────────────
def _audit_project(cur, project_id: int, lote_id: int, base_url: str) -> tuple:
    """
    Audita un proyecto. Devuelve (reporte_txt: str, tupla_bd: tuple | None).
    Idéntica lógica a verificador.py, sin análisis IA.
    """
    try:
        cur.execute("""
            SELECT p.*,
                   a.nombre  AS area_nombre,
                   l.nombre  AS lineamiento_nombre,
                   COALESCE(f.fuente, f.nombre) AS financiamiento_nombre,
                   ep.nombre AS estado_nombre,
                   et.nombre AS etapa_nombre,
                   es.nombre AS postulacion_nombre,
                   s.nombre  AS sector_nombre
            FROM proyectos p
            LEFT JOIN areas                 a  ON p.area_id = a.id
            LEFT JOIN lineamientos_estrategicos l ON p.lineamiento_estrategico_id = l.id
            LEFT JOIN financiamientos       f  ON p.financiamiento_id = f.id
            LEFT JOIN estados_proyecto      ep ON p.estado_proyecto_id = ep.id
            LEFT JOIN etapas_proyecto       et ON p.etapa_proyecto_id = et.id
            LEFT JOIN estados_postulacion   es ON p.estado_postulacion_id = es.id
            LEFT JOIN sectores              s  ON p.sector_id = s.id
            WHERE p.id = %s
        """, (project_id,))
        project = cur.fetchone()
        if not project:
            return f"Error: Proyecto {project_id} no encontrado.", None

        # ── helpers ──
        prio_icons = {"CRÍTICO": "🔴", "ALTO": "🟠", "MEDIO": "🟡", "BAJO": "⚪"}
        prio_map   = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}

        def get_compromiso(plazo_str):
            try:
                days = int(re.search(r'\d+', plazo_str).group()) if re.search(r'\d+', plazo_str) else 30
            except Exception:
                days = 30
            return (datetime.now() + timedelta(days=days)).strftime('%d/%m/%Y')

        def get_val_pct(val):
            if val is None or val == "": return 0.0
            vs = str(val).lower().strip()
            if "no aplica" in vs or "n/a" in vs: return 100.0
            try:
                v = float(vs.replace('%','').strip())
                return v * 100.0 if (0 < v <= 1.1) else v
            except Exception:
                return 0.0

        alerts     = []
        scores     = {}
        r          = []
        sep        = "─" * 80

        # ── Dim 1 ──
        d1_valid = sum([
            bool(project['id']), bool(project['nombre']),
            bool(project['n_registro']), bool(project['area_nombre']),
            bool(project['unidad_vecinal']), bool(project['sector_nombre'])
        ])
        if not project['unidad_vecinal']:
            alerts.append(("MEDIO","M01","Unidad Vecinal vacía","30 días",project['profesional_1']))
        if not project['sector_nombre']:
            alerts.append(("BAJO","B01","Sector vacío","90 días",project['profesional_1']))
        scores['Dim1'] = (d1_valid / 6) * 100

        # ── Dim 2 ──
        raw_avance = float(project['avance_total_porcentaje'] or 0)
        avance_pct = raw_avance * 100 if (0 < raw_avance <= 1.0) else raw_avance
        if raw_avance == 1.0: avance_pct = 100.0

        etapa  = project['etapa_nombre']  or ""
        estado = project['estado_nombre'] or ""
        postulacion = project['postulacion_nombre'] or ""
        monto  = float(project['monto'] or 0)
        codigo = project['n_registro'] or ""
        area   = project['area_nombre'] or ""
        lineamiento  = project['lineamiento_nombre'] or ""
        profesional  = project['profesional_1'] or ""
        prioridad    = str(project.get('es_prioridad','NO')).upper()
        obs          = project['observaciones'] or ""
        diff_years   = (project['anno_ejecucion'] or 0) - (project['anno_elaboracion'] or 0)

        d2_valid = 3  # prioridad + finan_municipal + año_elab
        if project['financiamiento_nombre']: d2_valid += 1
        if monto > 0: d2_valid += 1
        if project['anno_ejecucion'] and diff_years <= 5: d2_valid += 1
        else: alerts.append(("MEDIO","A02",f"Brecha {diff_years}a elab-ejec","30 días","SECPLAC"))
        scores['Dim2'] = (d2_valid / 6) * 100

        # ── Dim 3 ──
        topo_val   = get_val_pct(project['topografia'])
        plani_val  = get_val_pct(project['planimetrias'])
        ing_val    = get_val_pct(project['ingenieria'])
        perfil_val = get_val_pct(project['perfil_tecnico_economico'])
        doc_val    = get_val_pct(project['documentos'])

        d3_valid = sum(1 for v in [topo_val,plani_val,ing_val,perfil_val,doc_val] if v >= 100)
        if avance_pct >= 100: d3_valid += 1
        if (avance_pct / 100.0) >= 1.0: d3_valid += 1
        scores['Dim3'] = (d3_valid / 7) * 100

        # ── Validaciones V001-V015 ──
        hoy = datetime.now()
        fecha_act = project['fecha_actualizacion']
        if isinstance(fecha_act, str):
            fecha_act = datetime.strptime(fecha_act, '%Y-%m-%d %H:%M:%S')
        dias_sin_act = (hoy - fecha_act).days if fecha_act else 999

        val_alerts = []
        if etapa == "Ejecución" and estado not in ["En ejecución","Ejecutado"]:
            val_alerts.append(("CRÍTICO","V001","Etapa Ejecución incompatible con estado","Inmediato",profesional))
        if (etapa == "Idea de Proyecto" and avance_pct > 30) or (etapa == "Factibilidad" and avance_pct < 80):
            val_alerts.append(("CRÍTICO","V002","Avance fuera de rango para etapa","Inmediato",profesional))
        if etapa == "Factibilidad" and (doc_val < 100 or plani_val < 100 or topo_val < 100):
            val_alerts.append(("CRÍTICO","V003","Documentación incompleta para factibilidad","Inmediato",profesional))
        if etapa in ["Factibilidad","Ejecución"] and not project['financiamiento_nombre']:
            val_alerts.append(("CRÍTICO","V004","Financiamiento requerido en etapas avanzadas","7 días",profesional))
        if etapa != "Idea de Proyecto" and not profesional:
            val_alerts.append(("CRÍTICO","V005","Profesional responsable requerido","Inmediato","SECPLAC"))
        if area in ["Vialidad","Saneamiento","Espacios Públicos"] and (not project['latitud'] or not project['longitud']):
            val_alerts.append(("CRÍTICO","V006","Coordenadas requeridas para obra física","7 días",profesional))
        if etapa in ["Idea de Proyecto","Perfil"] and postulacion == "Aprobado RS":
            val_alerts.append(("ALTO","V007","Postulación inconsistente con etapa temprana","7 días",profesional))
        if dias_sin_act > 90:
            val_alerts.append(("ALTO","V008",f"Sin actualización {dias_sin_act} días","7 días",profesional))
        if diff_years > 5:
            val_alerts.append(("ALTO","V009",f"Brecha excesiva {diff_years} años","30 días","SECPLAC"))
        if monto == 0 and etapa in ["Prefactibilidad","Factibilidad","Ejecución"]:
            val_alerts.append(("ALTO","V010","Monto $0 en etapa avanzada","15 días",profesional))
        if not codigo and etapa in ["Prefactibilidad","Factibilidad","Ejecución"]:
            val_alerts.append(("MEDIO","V011","Código requerido en etapas avanzadas","30 días",profesional))
        if project['unidad_vecinal'] and not project['sector_nombre']:
            val_alerts.append(("MEDIO","V012","Sector requerido con unidad vecinal","30 días",profesional))
        if abs((avance_pct/100.0) - float(project['avance_total_decimal'] or 0)) > 0.01:
            val_alerts.append(("MEDIO","V013","Inconsistencia avance % vs decimal","30 días","SISTEMA"))
        if not lineamiento and prioridad == "SI":
            val_alerts.append(("BAJO","V014","Lineamiento requerido para prioritarios","90 días",profesional))
        if not obs and estado != "En preparación":
            val_alerts.append(("BAJO","V015","Se recomiendan observaciones","90 días",profesional))
        if not project['dupla_profesionales'] and etapa in ["Ejecución","Licitación"]:
            val_alerts.append(("BAJO","B02","Definir Dupla Profesional","90 días",profesional))

        # ── Validaciones cruzadas ──
        cur.execute("SELECT COUNT(*) FROM proyectos_documentos WHERE proyecto_id = %s", (project_id,))
        count_docs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM proyectos_observaciones WHERE proyecto_id = %s", (project_id,))
        count_obs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM proyectos_hitos WHERE proyecto_id = %s", (project_id,))
        count_hitos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM proximos_pasos WHERE proyecto_id = %s", (project_id,))
        count_pasos = cur.fetchone()[0]

        vi_alerts = []
        if etapa != "Idea de Proyecto" and count_docs == 0:
            vi_alerts.append(("CRÍTICO","VI001",f"Sin documentos en etapa {etapa}","Inmediato",profesional))
        if count_pasos == 0:
            vi_alerts.append(("CRÍTICO","VI007","Sin próximos pasos definidos","Inmediato",profesional))

        alerts.extend(val_alerts)
        alerts.extend(vi_alerts)

        high_alerts = [a for a in alerts if a[0] in ["CRÍTICO","ALTO"]]
        has_errors  = len(high_alerts) > 0

        conteo_crit = len([a for a in alerts if a[0] == "CRÍTICO"])
        conteo_alto = len([a for a in alerts if a[0] == "ALTO"])
        scores['Dim4'] = max(0, 100 - (conteo_crit*40) - (conteo_alto*15))

        final_score = (
            scores['Dim1'] * 0.10 + scores['Dim2'] * 0.15 + scores['Dim3'] * 0.20 +
            scores['Dim4'] * 0.25 + (100 if profesional else 0) * 0.10 +
            50.0 * 0.10 + (100 if project['latitud'] else 0) * 0.10
        )

        sorted_alerts = sorted(alerts, key=lambda x: prio_map.get(x[0], 99))

        # ── Acciones map ──
        acciones_map = {
            "V001": f"Corregir Etapa '{etapa}' a 'Factibilidad'",
            "V002": f"Ajustar Avance ({avance_pct}%) al rango para {etapa}",
            "V003": "Completar carga técnica (Topo/Plani/Doc 100%)",
            "V004": "Registrar fuente de financiamiento oficial",
            "V005": f"Asignar Profesional Responsable ({profesional or 'SECPLAC'})",
            "V006": "Georreferenciar: Ingresar Lat/Long",
            "V007": "Regularizar Postulación (RS incompatible con Idea/Perfil)",
            "V008": "Actualizar ficha (BD desactualizada)",
            "V009": f"Revisar cronograma: brecha {diff_years} años > límite 5",
            "V010": "Definir monto de inversión estimado",
            "V011": "Asignar Código de Proyecto definitivo",
            "V012": "Definir Sector para Unidad Vecinal asignada",
            "V013": "Sincronizar avance decimal vs porcentual",
            "V014": "Vincular Lineamiento Estratégico al proyecto prioritario",
            "V015": "Registrar Observaciones técnicas de seguimiento",
            "VI001": f"Subir archivos de respaldo para etapa {etapa}",
            "VI007": "Definir al menos 1 Próximo Paso para el proyecto",
            "A02":  f"Revisar brecha {diff_years} años elab-ejec",
            "M01": "Completar Unidad Vecinal",
            "B01": "Registrar sector territorial",
            "B02": "Definir Dupla Profesional supervisora",
        }
        field_map = {
            "V001":"etapa_proyecto_id","V002":"avance_total_porcentaje",
            "V003":"documentosContainer","V004":"financiamiento_id",
            "V005":"profesional_1","V006":"latitud",
            "V007":"estado_postulacion_id","V008":"fecha_actualizacion",
            "V009":"anno_ejecucion","V010":"monto","V011":"codigo",
            "V012":"sector_id","V013":"avance_total_porcentaje",
            "V014":"lineamiento_estrategico_id","V015":"observaciones",
            "VI001":"documentosContainer","VI007":"proximosPasosContainer",
            "A02":"anno_ejecucion","M01":"unidad_vecinal","B01":"sector_id","B02":"dupla_profesionales",
        }

        # ── Construcción del reporte ──
        r.append(f"📋 REPORTE DE CALIDAD INTEGRAL - PROYECTO ID: {project_id}")
        r.append(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        r.append(f"Sistema Multi-Dimensional de Auditoría Algarrobo (V4.0)")
        r.append(sep)
        r.append("🎯 RESUMEN DE IDENTIFICACIÓN")
        r.append(f"{'Nombre:':<20} {project['nombre']}")
        r.append(f"{'Código:':<20} {project['n_registro'] or 'PENDIENTE'}")
        r.append(f"{'Área:':<20} {project['area_nombre']}")
        r.append(f"{'Estado:':<20} {project['estado_nombre']}")
        r.append(sep)

        # Dims 1-3
        for dim_label, rows_extra, dim_score_key in [
            ("📊 DIMENSIÓN 1: IDENTIFICACIÓN Y CLASIFICACIÓN", [
                ('N° Registro', project['n_registro'] or '-', 'Formato ID'),
                ('Área Temática', project['area_nombre'] or '-', 'Lista maestra'),
                ('Unidad Vecinal', project['unidad_vecinal'] or '-', 'Cobertura'),
            ], 'Dim1'),
            ("📊 DIMENSIÓN 2: PRIORIZACIÓN Y FINANCIAMIENTO", [
                ('Monto Presup.', f"${monto:,.0f}", 'Base monetaria'),
                ('Fuente Finan.', project['financiamiento_nombre'] or '-', 'Origen'),
            ], 'Dim2'),
            ("📊 DIMENSIÓN 3: VARIABLES TÉCNICAS (Documentación)", [
                ('Topografía', project['topografia'] or '0%', 'Coherente'),
                ('Planimetrías', project['planimetrias'] or '0%', 'Coherente'),
                ('Ingeniería', project['ingenieria'] or '0%', 'Coherente'),
                ('Perfil Técnico', project['perfil_tecnico_economico'] or '0%', 'Coherente'),
                ('Documentos', project['documentos'] or '0%', 'Requerido'),
            ], 'Dim3'),
        ]:
            r.append(dim_label)
            r.append(f"{'Variable':<25}\t{'Valor':<15}\t{'Validación':<20}\t{'Resultado'}")
            for var_name, val, valid in rows_extra:
                r.append(f"{var_name:<25}\t{val:<15}\t{valid:<20}\t{'✅ Válido'}")
            r.append(f"Puntaje {dim_score_key}: {scores[dim_score_key]:.0f}%")
            r.append(sep)

        # Dim 4
        r.append(f"📊 DIMENSIÓN 4: ESTADO Y CICLO DE VIDA {'⚠️' if has_errors else ''}")
        r.append(f"{'Variable':<25}\t{'Valor':<15}\t{'Validación':<20}\t{'Resultado'}")
        r.append(f"{'Etapa':<25}\t{etapa:<15}\t{'Lista válida':<20}\t{'✅ Válido'}")
        r.append(f"{'Estado':<25}\t{(estado or '-'):<15}\t{'Lista válida':<20}\t{'✅ Válido'}")
        res_post  = "⚠️ Inconsistente" if has_errors else "✅ Válido"
        res_pasos = "🔴 Faltante" if count_pasos == 0 else "✅ Definido"
        r.append(f"{'Postulación':<25}\t{(postulacion or '-'):<15}\t{'Coherente':<20}\t{res_post}")
        r.append(f"{'Próximos Pasos':<25}\t{str(count_pasos):<15}\t{'Continuidad':<20}\t{res_pasos}")
        if has_errors:
            r.append("\n🔴 ALERTAS DE ALTA PRIORIDAD DETECTADAS")
            for a in high_alerts:
                r.append(f"• [{a[1]}] {a[2]} ({a[0]})")
        r.append(f"Puntaje Dim4: {scores['Dim4']:.0f}%")
        r.append(sep)

        # Dims 5-7
        r.append("📊 DIMENSIÓN 5: EQUIPO PROFESIONAL")
        r.append(f"{'Profesional 1':<25}\t{profesional or '-':<15}\t{'Responsabilidad':<20}\t{'✅ Asignado' if profesional else '⚠️ Pendiente'}")
        r.append(f"Puntaje Dim5: {100 if profesional else 0}%")
        r.append(sep)
        r.append("📊 DIMENSIÓN 6: APROBACIONES Y PERMISOS")
        r.append(f"{'Aprobación DOM':<25}\t{(project['aprobacion_dom'] or 'No'):<15}\t{'Requerido':<20}\t{'✅ Sí' if project['aprobacion_dom'] == 'SÍ' else '⚠️ No/Pendiente'}")
        r.append("Puntaje Dim6: 50%")
        r.append(sep)
        r.append("📊 DIMENSIÓN 7: VARIABLES GEOGRÁFICAS")
        geo_res = "✅ Válido" if project['latitud'] else "⚠️ Faltante"
        r.append(f"{'Latitud':<25}\t{(project['latitud'] or '-'):<15}\t{'Obra física':<20}\t{geo_res}")
        r.append(f"{'Longitud':<25}\t{(project['longitud'] or '-'):<15}\t{'Obra física':<20}\t{geo_res}")
        r.append(f"Puntaje Dim7: {100 if project['latitud'] else 0}%")
        r.append(sep)

        # Resumen alertas
        r.append("🚨 RESUMEN DE ALERTAS GENERADAS")
        r.append(f"{'Nivel':<10}\t{'Código':<10}\t{'Descripción':<40}\t{'Plazo':<10}\t{'Responsable'}")
        for a in sorted_alerts:
            r.append(f"{a[0]:<10}\t{a[1]:<10}\t{a[2][:40]:<40}\t{a[3]:<10}\t{a[4] or '-'}")
        r.append(sep)

        # Puntaje general
        r.append("📈 PUNTAJE DE CALIDAD DEL PROYECTO")
        r.append(f"{'Dimensión':<30}\t{'Puntaje':<10}\t{'Peso':<8}\t{'Ponderado'}")
        for dim_name, sk, peso in [
            ("Identificación","Dim1",0.10),("Priorización","Dim2",0.15),
            ("Variables Técnicas","Dim3",0.20),("Estado y Ciclo","Dim4",0.25),
        ]:
            r.append(f"{dim_name:<30}\t{scores[sk]:>6.0f}%\t{int(peso*100)}%\t{scores[sk]*peso:>8.1f}")
        r.append(f"\nCALIDAD GENERAL: {final_score:.1f}% {'⚠️ Requiere atención' if final_score < 80 else ''}")

        filled = int(max(0, min(100, final_score)) / 100 * 40)
        r.append("\n0%        25%        50%        75%       100%")
        r.append("|──────────|──────────|──────────|──────────|")
        r.append("█" * filled + "░" * (40 - filled) + f"  {final_score:.1f}%")
        r.append(sep)

        # Plan de acción
        r.append("✅ PLAN DE ACCIÓN CORRECTIVO")
        r.append(f"{'Prioridad':<10}\t{'Acción':<50}\t{'Responsable':<12}\t{'Plazo':<10}\t{'Estado':<12}\t{'Fecha Compromiso'}\t{'Enlace'}")
        for i, a in enumerate(sorted_alerts, 1):
            icon    = prio_icons.get(a[0], "⚪")
            cod     = a[1]
            accion  = acciones_map.get(cod, a[2])
            resp    = a[4] or profesional or "SECPLAC"
            plazo   = a[3]
            comp    = get_compromiso(plazo)
            tf      = field_map.get(cod, "nombre")
            url     = f"{base_url}/frontend/division/secplan/admin_general/proyecto.html?pid={project_id}&audit_field={tf}"
            r.append(f"{icon}{i:<9}\t{accion:<50}\t{resp:<12}\t{plazo:<10}\t{'Pendiente':<12}\t{comp}\t[Corregir]({url})")
        r.append(sep)

        final_report = "\n".join(r)

        # ── Tupla para BD ──
        tupla_bd = (
            lote_id, project_id,
            project.get('n_registro'), project.get('nombre'), project.get('area_id'),
            project.get('lineamiento_estrategico_id'), project.get('financiamiento_id'),
            project.get('financiamiento_municipal'), project.get('monto'),
            project.get('anno_elaboracion'), project.get('anno_ejecucion'),
            project.get('topografia'), project.get('planimetrias'), project.get('ingenieria'),
            project.get('perfil_tecnico_economico'), project.get('documentos'),
            project.get('avance_total_porcentaje'), project.get('avance_total_decimal'),
            project.get('estado_proyecto_id'), project.get('etapa_proyecto_id'),
            project.get('estado_postulacion_id'), project.get('fecha_postulacion'),
            project.get('dupla_profesionales'), project.get('profesional_1'),
            project.get('profesional_2'), project.get('profesional_3'),
            project.get('profesional_4'), project.get('profesional_5'),
            project.get('unidad_vecinal'), project.get('sector_id'),
            project.get('aprobacion_dom'), project.get('aprobacion_serviu'),
            project.get('latitud'), project.get('longitud'),
            project.get('observaciones'), project.get('activo'),
            count_docs, count_hitos, count_obs, count_pasos,
            final_score,
            scores.get('Dim1',0), scores.get('Dim2',0),
            scores.get('Dim3',0), scores.get('Dim4',0),
            (100 if profesional else 0), 50, (100 if project['latitud'] else 0),
            avance_pct, etapa, estado,
            len([a for a in alerts if a[0]=="CRÍTICO"]),
            len([a for a in alerts if a[0]=="ALTO"]),
            len([a for a in alerts if a[0]=="MEDIO"]),
            len([a for a in alerts if a[0]=="BAJO"]),
            json.dumps(alerts, default=str),
        )
        return final_report, tupla_bd

    except Exception as e:
        logger.error(f"audit_project error pid={project_id}: {e}")
        return f"Error proyecto {project_id}: {str(e)}", None


# ──────────────────────────────────────────────
# MOTOR DE HISTORIAL Y CAMBIOS (Basado en verificador2.py)
# ──────────────────────────────────────────────
def _audit_history(cur, project_id: int) -> str:
    """Extrae historial de avances (auditoria_proyectos) y cambios (control_actividad)."""
    try:
        cur.execute("SELECT n_registro, nombre FROM proyectos WHERE id = %s", (project_id,))
        p = cur.fetchone()
        if not p: return ""
        
        r = []
        sep = "─" * 80
        r.append(f"📋 REPORTE DE HISTORIAL Y AVANCES DEL PROYECTO")
        r.append(f"ID DEL PROYECTO: {project_id} | CÓDIGO: {p['n_registro'] or 'PENDIENTE'}")
        r.append(f"NOMBRE: {p['nombre']}")
        r.append(sep)

        # 1. Avances desde auditoría
        cur.execute("""
            SELECT 
                al.fecha_ejecucion, 
                ap.avance_declarado, 
                LAG(ap.avance_declarado) OVER (ORDER BY al.fecha_ejecucion ASC) as prev_avance,
                ap.etapa, 
                LAG(ap.etapa) OVER (ORDER BY al.fecha_ejecucion ASC) as prev_etapa,
                ap.puntaje_general, 
                LAG(ap.puntaje_general) OVER (ORDER BY al.fecha_ejecucion ASC) as prev_puntaje,
                ap.alertas_criticas,
                LAG(ap.alertas_criticas) OVER (ORDER BY al.fecha_ejecucion ASC) as prev_criticas
            FROM auditoria_proyectos ap
            JOIN auditoria_lotes al ON ap.lote_id = al.id
            WHERE ap.proyecto_id = %s
            ORDER BY al.fecha_ejecucion DESC
        """, (project_id,))
        auds = cur.fetchall()

        r.append("📈 SECUENCIA DE AVANCES Y REVISIONES (Desde Snapshot Auditoría)")
        if not auds:
            r.append("No hay registros históricos de auditoría.")
        else:
            r.append(f"{'Fecha Auditoría':<16}\t{'Avance (Ant ➔ Act)':<22}\t{'Etapa (Anterior ➔ Actual)':<40}\t{'Puntaje (Ant ➔ Act)':<22}\t{'Críticas'}")
            for a in auds:
                f = a['fecha_ejecucion'].strftime("%d/%m/%y %H:%M") if a['fecha_ejecucion'] else "-"
                def np(v):
                    if v is None: return 0.0
                    vf = float(v)
                    return vf * 100 if (0 < vf <= 1.0) else vf
                
                av_a = np(a['prev_avance'])
                av_n = np(a['avance_declarado'])
                av_s = f"{av_a:.0f}% ➔ {av_n:.0f}%" if f"{av_a:.0f}" != f"{av_n:.0f}" else f"{av_n:.0f}%"
                
                et_a = a['prev_etapa'] or "Inicio"
                et_n = a['etapa'] or "-"
                et_s = f"{et_a} ➔ {et_n}" if et_a != et_n else et_n
                
                pt_a = np(a['prev_puntaje'])
                pt_n = np(a['puntaje_general'])
                pt_s = f"{pt_a:.0f}% ➔ {pt_n:.0f}%" if f"{pt_a:.0f}" != f"{pt_n:.0f}" else f"{pt_n:.0f}%"
                
                cr_a = a['prev_criticas'] or 0
                cr_n = a['alertas_criticas'] or 0
                cr_s = f"{cr_a} ➔ {cr_n}" if cr_a != cr_n else str(cr_n)
                
                r.append(f"{f:<16}\t{av_s:<22}\t{et_s:<40}\t{pt_s:<22}\t{cr_s}")
        r.append(sep)

        # 2. Cambios desde control_actividad
        cur.execute("""
            SELECT c.fecha, c.accion, u.nombre as autor, c.detalle, c.datos_antes, c.datos_despues
            FROM control_actividad c
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE c.entidad_tipo = 'proyecto' AND c.entidad_id = %s
            ORDER BY c.fecha DESC
            LIMIT 50
        """, (project_id,))
        logs = cur.fetchall()

        r.append("🕒 HISTORIAL COMPLETO DE ACCIONES Y CAMBIOS DEL PROYECTO")
        if not logs:
            r.append("No hay registros de actividad específica para este proyecto.")
        else:
            r.append(f"{'Fecha':<16}\t{'Acción':<20}\t{'Autor':<15}\t{'Detalle / Cambios Modificados'}")
            for l in logs:
                f = l['fecha'].strftime("%d/%m/%y %H:%M") if l['fecha'] else "-"
                ac = str(l['accion'])[:20]
                au = str(l['autor'] or "Sistema")[:15]
                dt = l['detalle'] or ""
                
                if l['accion'] == 'editar_proyecto':
                    try:
                        ant = l['datos_antes'] or {}
                        des = l['datos_despues'] or {}
                        if isinstance(ant, str): ant = json.loads(ant)
                        if isinstance(des, str): des = json.loads(des)
                        cambios = []
                        for k, v in des.items():
                            v0 = ant.get(k)
                            if str(v) != str(v0) and k not in ['fecha_actualizacion','user_id']:
                                label = k.replace('_',' ').title()
                                cambios.append(f"{label}: [{v0}] ➔ [{v}]")
                        if cambios: dt = "CAMBIOS: " + " | ".join(cambios)
                    except: pass
                
                if len(dt) > 200: dt = dt[:197] + "..."
                r.append(f"{f:<16}\t{ac:<20}\t{au:<15}\t{dt}")
        
        r.append(sep)
        return "\n".join(r)
    except Exception as e:
        logger.error(f"Error _audit_history pid={project_id}: {e}")
        return f"Error extrayendo historial: {str(e)}"


# ──────────────────────────────────────────────
# TAREA ASÍNCRONA PRINCIPAL
# ──────────────────────────────────────────────
def run_auditoria_async(db_factory, release_fn, ejecutor_nombre: str,
                        base_url: str = "https://geoportalalgarrobo.github.io/ALGARROBO_BASE2"):
    """
    Lanza la auditoría en un hilo secundario.
    db_factory  → función sin args que retorna una conexión psycopg2
    release_fn  → función(conn) para devolver la conexión al pool
    ejecutor_nombre → Nombre del usuario que inicia la ejecución
    Retorna True si la tarea se lanzó, False si ya había una en curso.
    """
    with _task_lock:
        if _task_status["running"]:
            return False
        _task_status.update({
            "running": True, "lote_id": None, "total": 0,
            "procesados": 0, "errores": 0,
            "iniciado_en": datetime.now().isoformat(),
            "finalizado_en": None, "ejecutado_por": ejecutor_nombre, "error_fatal": None,
        })

    t = threading.Thread(target=_worker, args=(db_factory, release_fn, ejecutor_nombre, base_url),
                         daemon=True)
    t.start()
    return True


def _worker(db_factory, release_fn, ejecutor_nombre, base_url):
    """Hilo de trabajo de la auditoría."""
    import psycopg2.extras

    conn = None
    try:
        conn = db_factory()

        # ── Limpiar ejecución anterior ──
        import shutil
        if os.path.exists(AUDIT_OUT_DIR):
            shutil.rmtree(AUDIT_OUT_DIR)
        os.makedirs(AUDIT_OUT_DIR, exist_ok=True)

        # ── Obtener IDs ──
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM proyectos ORDER BY id ASC")
            ids = [row[0] for row in cur.fetchall()]

        _update_status(total=len(ids))

        if not ids:
            _update_status(running=False, finalizado_en=datetime.now().isoformat(),
                           error_fatal="Sin proyectos para auditar")
            return

        # ── Crear lote ──
        lote_id = None
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO auditoria_lotes (total_proyectos_auditados, usuario_ejecutor)
                    VALUES (%s, %s) RETURNING id
                """, (len(ids), str(ejecutor_nombre)))
                lote_id = cur.fetchone()[0]
            conn.commit()
            _update_status(lote_id=lote_id)
        except Exception as e:
            logger.warning(f"No se pudo crear lote: {e}")
            # intentamos con la columna genérica
            try:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO auditoria_lotes (total_proyectos_auditados) VALUES (%s) RETURNING id",
                                (len(ids),))
                    lote_id = cur.fetchone()[0]
                conn.commit()
                _update_status(lote_id=lote_id)
            except Exception as e2:
                logger.error(f"Fallo creación lote: {e2}")

        # ── Procesar proyectos ──
        batch = []
        errors = 0

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            for i, pid in enumerate(ids, 1):
                try:
                    # Reporte 1: Calidad (verificador.py)
                    report_txt, tupla = _audit_project(cur, pid, lote_id, base_url)
                    pdf_path = os.path.join(AUDIT_OUT_DIR, f"Auditoria_Proyecto_{pid}.pdf")
                    _generate_pdf(report_txt.split('\n'), pdf_path)

                    # Reporte 2: Historial y Cambios (verificador2.py)
                    history_txt = _audit_history(cur, pid)
                    if history_txt:
                        hist_pdf_path = os.path.join(AUDIT_OUT_DIR, f"Historial_Cambios_Proyecto_{pid}.pdf")
                        _generate_pdf(history_txt.split('\n'), hist_pdf_path)

                    if tupla:
                        batch.append(tupla)
                except Exception as e:
                    logger.error(f"Error pid={pid}: {e}")
                    errors += 1

                _update_status(procesados=i, errores=errors)

        # ── Volcado BD ──
        if lote_id and batch:
            try:
                import psycopg2.extras as _ext
                with conn.cursor() as cur:
                    q = """
                        INSERT INTO auditoria_proyectos (
                            lote_id, proyecto_id,
                            n_registro, nombre, area_id, lineamiento_estrategico_id,
                            financiamiento_id, financiamiento_municipal, monto,
                            anno_elaboracion, anno_ejecucion,
                            topografia, planimetrias, ingenieria,
                            perfil_tecnico_economico, documentos,
                            avance_total_porcentaje, avance_total_decimal,
                            estado_proyecto_id, etapa_proyecto_id, estado_postulacion_id, fecha_postulacion,
                            dupla_profesionales, profesional_1, profesional_2, profesional_3,
                            profesional_4, profesional_5,
                            unidad_vecinal, sector_id, aprobacion_dom, aprobacion_serviu,
                            latitud, longitud, observaciones, activo,
                            cant_documentos, cant_hitos, cant_observaciones, cant_proximos_pasos,
                            puntaje_general, puntaje_d1, puntaje_d2, puntaje_d3, puntaje_d4,
                            puntaje_d5, puntaje_d6, puntaje_d7,
                            avance_declarado, etapa, estado,
                            alertas_criticas, alertas_altas, alertas_medias, alertas_bajas,
                            alertas_json
                        ) VALUES %s
                    """
                    _ext.execute_values(cur, q, batch)
                    cur.execute("""
                        UPDATE auditoria_lotes
                        SET promedio_calidad_general = (
                            SELECT COALESCE(AVG(puntaje_general),0)
                            FROM auditoria_proyectos WHERE lote_id = %s
                        ) WHERE id = %s
                    """, (lote_id, lote_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Error volcado BD: {e}")

        _update_status(running=False, finalizado_en=datetime.now().isoformat(), errores=errors)

    except Exception as e:
        logger.error(f"Error fatal worker auditoría: {e}")
        _update_status(running=False, error_fatal=str(e),
                       finalizado_en=datetime.now().isoformat())
    finally:
        if conn:
            release_fn(conn)
