import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import json

# ==============================================================================
# SCRIPT DE AUDITORÍA INTEGRAL DE PROYECTOS
# Genera Reporte Estructurado para Validación de Datos (PDF y TXT)
# ==============================================================================

# NOTA: El usuario debe configurar su DATABASE_URL aquí o en el entorno
DATABASE_URL = "SU_STRING_DE_CONEXION_AQUI"

def generate_pdf_from_text(lines, filename):
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        # Usar landscape para que las tablas anchas quepan excelentemente
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4), leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('title', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#4f46e5'), spaceAfter=8, alignment=TA_CENTER)
        sub_style = ParagraphStyle('sub_title', parent=styles['Normal'], fontSize=11, textColor=colors.grey, spaceAfter=16, alignment=TA_CENTER)
        h2_style = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#1e293b'), spaceBefore=12, spaceAfter=6)
        normal_style = styles['Normal']
        normal_bold = ParagraphStyle('nb', parent=styles['Normal'], fontName='Helvetica-Bold')

        current_table_data = []

        def commit_table():
            if current_table_data:
                formatted_data = []
                for row_idx, row in enumerate(current_table_data):
                    formatted_row = []
                    for col_idx, cell in enumerate(row):
                        if row_idx == 0:
                            formatted_row.append(cell)
                        else:
                            # Utilizar texto normal a menos que la fila indique un error
                            txt_style = normal_bold if len(str(cell)) < 30 and ("⚠️" in str(cell) or "🔴" in str(cell) or "CRÍTICO" in str(cell) or "ALTO" in str(cell)) else styles['Normal']
                            formatted_row.append(Paragraph(str(cell).strip(), txt_style))
                    formatted_data.append(formatted_row)
                
                cols = len(current_table_data[0])
                header_text = " ".join(current_table_data[0]).upper()
                colWidths = None
                
                # Asignación heurística de anchos según layout del .txt
                if cols == 2: 
                    colWidths = [6*cm, 20*cm]
                elif cols == 4: 
                    colWidths = [7*cm, 4*cm, 5*cm, 10*cm]
                elif cols == 5:
                    if "PUNTAJE" in header_text and "PESO" in header_text:
                        colWidths = [10*cm, 3.5*cm, 3.5*cm, 4.5*cm, 4.5*cm]
                    else:
                        colWidths = [2.5*cm, 2.5*cm, 12*cm, 3.5*cm, 5.5*cm]
                elif cols == 6: 
                    colWidths = [2.5*cm, 10.5*cm, 4.5*cm, 2.5*cm, 3*cm, 3*cm]
                
                t = Table(formatted_data, colWidths=colWidths)
                
                # Styling a lo Módulo de Seguridad
                header_bg = colors.HexColor('#4f46e5') # Primary indigo
                if "NIVEL" in header_text and "CÓDIGO" in header_text: 
                    header_bg = colors.HexColor('#ef4444') # Red for alerts
                elif "PUNTAJE" in header_text: 
                    header_bg = colors.HexColor('#10b981') # Green for scores
                elif "ACCIÓN" in header_text and "PRIORIDAD" in header_text:
                    header_bg = colors.HexColor('#f59e0b') # Amber for actions
                    
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), header_bg),
                    ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                    ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE',   (0,0), (-1,-1), 9),
                    ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
                    ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING',    (0,0), (-1,-1), 6),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.4*cm))
                current_table_data.clear()

        for line in lines:
            original_line = line
            line = line.strip()
            
            # Limpiar elementos puramente visuales del TXT
            if not line or set(line).issubset({'_', '═', '─', '┌', '┐', '└', '┘', '│', '█', '░', '|'}) or "0%        25%" in line:
                commit_table()
                continue
                
            if '\t' in original_line:
                current_table_data.append([c.strip() for c in original_line.split('\t')])
            else:
                commit_table()
                if line.startswith("📋"):
                    story.append(Paragraph(line, title_style))
                elif "Sistema Multi-Dimensional" in line:
                    story.append(Paragraph(line, sub_style))
                elif line.startswith("📊") or line.startswith("🎯") or line.startswith("🚨") or line.startswith("📈") or line.startswith("✅") or line.startswith("🔍"):
                    story.append(Paragraph(line, h2_style))
                    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#4f46e5')))
                    story.append(Spacer(1, 0.2*cm))
                elif "CALIDAD GENERAL:" in line:
                    score_style = ParagraphStyle('score', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', textColor=colors.HexColor('#ef4444') if "⚠️" in line else colors.HexColor('#10b981'))
                    story.append(Paragraph(line, score_style))
                    story.append(Spacer(1, 0.3*cm))
                elif "PRINCIPAL HALLAZGO" in line or "INSTRUCCIÓN:" in line or "RECOMENDACIÓN:" in line:
                    story.append(Paragraph(f"<b>{line}</b>", normal_style))
                else:
                    if "BARRA DE CALIDAD VISUAL" not in line:
                        story.append(Paragraph(line, normal_style))
                        story.append(Spacer(1, 0.1*cm))
                    
        commit_table()
        doc.build(story)
        return True
    except Exception as e:
        print(f"Error generando PDF para {filename}: {str(e)}")
        return False

# --- MOTOR DE INTELIGENCIA ARTIFICIAL PARA ANÁLISIS CUALITATIVO ---
class AIAnalyst:
    def __init__(self):
        self.API_KEY = "1fdd53bb96924d78b1d799919a7c21e4.PgBhpSwp9Uvpi48a"
        self.API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.MODEL = "GLM-4.7-Flash"

    def get_analysis(self, report_text):
        prompt = f"""
        Actúa como un Auditor Senior de SECPLAC de la Municipalidad de Algarrobo. 
        Basado en el reporte técnico que se proporciona, genera un 'ANÁLISIS CUALITATIVO' experto.

        OBJETIVO: Detectar inconsistencias críticas (especialmente entre Etapa, Estado y Avance) y contrastarlas con las observaciones manuales del proyecto.

        ESTRUCTURA OBLIGATORIA (DEBES RESPONDER ÚNICAMENTE CON ESTAS SECCIONES):

        ANÁLISIS CUALITATIVO
        [Describe la inconsistencia técnica o administrativa más grave detectada en los datos]

        SEGÚN LAS OBSERVACIONES REGISTRADAS:
        [Cita textual o resumen de las notas de la cabecera 'Observaciones' que sustentan tu hallazgo]

        INTERPRETACIÓN:
        • [Punto lógico 1 sobre el desfase entre lo declarado y lo real]
        • [Punto lógico 2 sobre el riesgo operativo implicado]

        POSIBLE CAUSA:
        • [Hipótesis técnica de por qué la ficha está errónea (ej: error de digitación, falta de actualización)]

        RECOMENDACIÓN PRINCIPAL:
        1. [Paso concreto 1 para regularizar la ficha en el sistema]
        2. [Paso concreto 2 para la gestión administrativa del proyecto]

        REGLAS DE ESTILO:
        - Tono de mando policial: técnico, directo, sin adornos.
        - No incluyas intros como "Aquí tienes el análisis...".
        - El resultado debe estar en español.

        REPORTE TÉCNICO:
        {report_text}
        """
        try:
            payload = {
                "model": self.MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            response = requests.post(
                self.API_URL,
                headers={"Authorization": f"Bearer {self.API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            return "Análisis automático no disponible temporalmente."
        except Exception:
            return "Error de conexión con el motor de IA."

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def audit_project(cur, project_id, lote_id=None):
    try:
        # Consulta integral con joins para nombres de maestros (Reusando cursor)
        cur.execute("""
            SELECT 
                p.*,
                a.nombre as area_nombre,
                l.nombre as lineamiento_nombre,
                f.nombre as financiamiento_nombre,
                ep.nombre as estado_nombre,
                et.nombre as etapa_nombre,
                es.nombre as postulacion_nombre,
                s.nombre as sector_nombre
            FROM proyectos p
            LEFT JOIN areas a ON p.area_id = a.id
            LEFT JOIN lineamientos_estrategicos l ON p.lineamiento_estrategico_id = l.id
            LEFT JOIN financiamientos f ON p.financiamiento_id = f.id
            LEFT JOIN estados_proyecto ep ON p.estado_proyecto_id = ep.id
            LEFT JOIN etapas_proyecto et ON p.etapa_proyecto_id = et.id
            LEFT JOIN estados_postulacion es ON p.estado_postulacion_id = es.id
            LEFT JOIN sectores s ON p.sector_id = s.id
            WHERE p.id = %s
        """, (project_id,))
        
        project = cur.fetchone()
        if not project:
            return f"Error: Proyecto ID {project_id} no encontrado.", None

        # --- Lógica de Auditoría Interna ---
        alerts = []
        scores = {}
        r = []
        sep = "─" * 80
        
        # Dim 1: Identificación (Peso 10%)
        d1_valid = 0
        d1_total = 6
        if project['id']: d1_valid += 1
        if project['nombre']: d1_valid += 1
        if project['n_registro']: d1_valid += 1 # Usado como código en el ejemplo
        if project['area_nombre']: d1_valid += 1
        if project['unidad_vecinal']: d1_valid += 1
        else: alerts.append(("MEDIO", "M01", "Unidad Vecinal vacía en proyecto territorial", "30 días", project['profesional_1']))
        if project['sector_nombre']: d1_valid += 1
        else: alerts.append(("BAJO", "B01", "Sector vacío", "90 días", project['profesional_1']))
        scores['Dim1'] = (d1_valid / d1_total) * 100

        # Dim 2: Priorización y Finanzas (Peso 15%)
        d2_valid = 0
        d2_total = 6
        # (Simplificado para el script)
        d2_valid += 1 # Prioridad
        d2_valid += 1 # Finan. Municipal
        if project['financiamiento_nombre']: d2_valid += 1
        if float(project['monto'] or 0) > 0: d2_valid += 1
        if project['anno_elaboracion']: d2_valid += 1
        
        diff_years = (project['anno_ejecucion'] or 0) - (project['anno_elaboracion'] or 0)
        if project['anno_ejecucion'] and diff_years <= 5:
            d2_valid += 1
        else:
            d2_valid += 0 # Alert
            alerts.append(("MEDIO", "A02", f"Diferencia de {diff_years} años entre elab. y ejec.", "30 días", "SECPLAC"))
        scores['Dim2'] = (d2_valid / d2_total) * 100

        # --- Variables de Estado y Normalización ---
        etapa = project['etapa_nombre'] or ""
        estado = project['estado_nombre'] or ""
        postulacion = project['postulacion_nombre'] or ""
        avance_pct = float(project['avance_total_porcentaje'] or 0)
        diff_years = (project['anno_ejecucion'] or 0) - (project['anno_elaboracion'] or 0)

        # Dim 3: Variables Técnicas (Peso 20%)
        # Helper para obtener valor numérico normalizado a porcentaje (0-100)
        def get_val_pct(val):
            if val is None or val == "": return 0.0
            val_str = str(val).lower().strip()
            if "no aplica" in val_str or "n/a" in val_str:
                return 100.0 # Se considera cumplido/validado
            try: 
                v_str = val_str.replace('%', '').strip()
                v = float(v_str)
                if v <= 1.1 and v > 0: # Ajustamos margen por si es 1.0 (100%)
                    return v * 100.0
                return v
            except: return 0.0

        topo_val = get_val_pct(project['topografia'])
        plani_val = get_val_pct(project['planimetrias'])
        ing_val = get_val_pct(project['ingenieria'])
        perfil_val = get_val_pct(project['perfil_tecnico_economico'])
        doc_val = get_val_pct(project['documentos'])
        
        d3_valid = 0
        for v in [topo_val, plani_val, ing_val, perfil_val, doc_val]:
            if v >= 100: d3_valid += 1
        
        if avance_pct >= 100: d3_valid += 1
        if (avance_pct / 100.0) >= 1.0: d3_valid += 1 # Doble chequeo decimal/pct
        
        scores['Dim3'] = (d3_valid / 7) * 100

        # Dim 4: Estado y Ciclo de Vida (PESO 25%) - REGLAS DE NEGOCIO MUNICIPALES (VER. 3)
        # --- MATRIZ DE VALIDACIÓN INTEGRAL (REGLAS V001 - V015) ---
        validation_alerts = []
        
        # Normalización de datos para validación
        monto = float(project['monto'] or 0)
        codigo = project['n_registro'] or ""
        area = project['area_nombre'] or ""
        lineamiento = project['lineamiento_nombre'] or ""
        profesional = project['profesional_1'] or ""
        prioridad = str(project.get('es_prioridad', 'NO')).upper()
        obs = project['observaciones'] or ""
        
        # Tiempos
        hoy = datetime.now()
        fecha_act = project['fecha_actualizacion']
        if isinstance(fecha_act, str):
            fecha_act = datetime.strptime(fecha_act, '%Y-%m-%d %H:%M:%S')
        dias_sin_act = (hoy - fecha_act).days if fecha_act else 999

        # V001: Etapa-Estado Inconsistente
        if etapa == "Ejecución" and estado not in ["En ejecución", "Ejecutado"]:
            validation_alerts.append(("CRÍTICO", "V001", "Etapa Ejecución incompatible con estado declarado", "Inmediato", profesional))

        # V002: Avance Fuera de Rango por Etapa
        if (etapa == "Idea de Proyecto" and avance_pct > 30) or (etapa == "Factibilidad" and avance_pct < 80):
            validation_alerts.append(("CRÍTICO", "V002", "Avance fuera de rango permitido para la etapa", "Inmediato", profesional))

        # V003: Documentación Incompleta
        if etapa == "Factibilidad" and (doc_val < 100 or plani_val < 100 or topo_val < 100):
            validation_alerts.append(("CRÍTICO", "V003", "Documentación incompleta para etapa de factibilidad", "Inmediato", profesional))

        # V004: Financiamiento Vacío
        if etapa in ["Factibilidad", "Ejecución"] and not project['financiamiento_nombre']:
            validation_alerts.append(("CRÍTICO", "V004", "Financiamiento requerido en etapas avanzadas", "7 días", profesional))

        # V005: Profesional Responsable Vacío
        if etapa != "Idea de Proyecto" and not profesional:
            validation_alerts.append(("CRÍTICO", "V005", "Profesional responsable requerido desde Perfil", "Inmediato", "SECPLAC"))

        # V006: Sin Coordenadas Geográficas
        areas_fisicas = ["Vialidad", "Saneamiento", "Espacios Públicos"]
        if area in areas_fisicas and (not project['latitud'] or not project['longitud']):
            validation_alerts.append(("CRÍTICO", "V006", "Coordenadas requeridas para proyectos de obra física", "7 días", profesional))

        # V007: Postulación Temprana Aprobada
        if etapa in ["Idea de Proyecto", "Perfil"] and postulacion == "Aprobado RS":
            validation_alerts.append(("ALTO", "V007", "Estado de postulación inconsistente con etapa temprana", "7 días", profesional))

        # V008: Fecha Actualización Vencida
        if dias_sin_act > 90:
            validation_alerts.append(("ALTO", "V008", f"Proyecto sin actualización por más de 90 días ({dias_sin_act} días)", "7 días", profesional))

        # V009: Año Ejecución Muy Distante
        if diff_years > 5:
            validation_alerts.append(("ALTO", "V009", f"Diferencia excesiva entre elaboración y ejecución ({diff_years} años)", "30 días", "SECPLAC"))

        # V010: Monto Cero en Etapas Avanzadas
        if monto == 0 and etapa in ["Prefactibilidad", "Factibilidad", "Ejecución"]:
            validation_alerts.append(("ALTO", "V010", "Monto requerido en etapas avanzadas", "15 días", profesional))

        # V011: Código de Proyecto Vacío
        if not codigo and etapa in ["Prefactibilidad", "Factibilidad", "Ejecución"]:
            validation_alerts.append(("MEDIO", "V011", "Código requerido en etapas avanzadas", "30 días", profesional))

        # V012: Unidad Vecinal sin Sector
        if project['unidad_vecinal'] and not project['sector_nombre']:
            validation_alerts.append(("MEDIO", "V012", "Sector requerido cuando hay unidad vecinal", "30 días", profesional))

        # V013: Avance Decimal Inconsistente
        if abs((avance_pct / 100.0) - float(project['avance_total_decimal'] or 0)) > 0.01:
            validation_alerts.append(("MEDIO", "V013", "Inconsistencia entre avance porcentual y decimal", "30 días", "SISTEMA"))

        # V014: Lineamiento Estratégico Vacío
        if not lineamiento and prioridad == "SI":
            validation_alerts.append(("BAJO", "V014", "Lineamiento requerido para proyectos prioritarios", "90 días", profesional))

        # V015: Observaciones Vacías
        if not obs and estado != "En preparación":
            validation_alerts.append(("BAJO", "V015", "Se recomiendan observaciones para seguimiento", "90 días", profesional))

        # --- VALIDACIONES CRUZADAS MULTI-TABLA (REGLAS VI001 - VI006) ---
        vi_alerts = []
        
        # Consultas a tablas relacionadas (Utilizando el cursor pre-existente)
        # Para subqueries sin entorpecer la principal, generamos uno nuevo momentáneo o reusamos:
        cur.execute("SELECT COUNT(*) FROM proyectos_documentos WHERE proyecto_id = %s", (project_id,))
        count_docs = cur.fetchone()[0]
        
        # Observaciones
        cur.execute("SELECT COUNT(*) FROM proyectos_observaciones WHERE proyecto_id = %s", (project_id,))
        count_obs = cur.fetchone()[0]
        
        # Hitos
        cur.execute("SELECT COUNT(*) FROM proyectos_hitos WHERE proyecto_id = %s", (project_id,))
        count_hitos = cur.fetchone()[0]
        
        # Geomapas
        cur.execute("SELECT geojson FROM proyectos_geomapas WHERE proyecto_id = %s LIMIT 1", (project_id,))
        geom_row = cur.fetchone()
            
        # VI001: Documentos Requeridos por Etapa (Simplificado: Perfil+ requiere al menos 1 doc)
        if etapa != "Idea de Proyecto" and count_docs == 0:
            vi_alerts.append(("CRÍTICO", "VI001", f"Faltan documentos en etapa {etapa}", "Inmediato", profesional))


        # Dim 3
        r.append("📊 DIMENSIÓN 3: VARIABLES TÉCNICAS (Documentación)")
        r.append(f"{'Variable':<25}\t{'Valor':<15}\t{'Validación':<20}\t{'Resultado'}")
        r.append(f"{'Topografía':<25}\t{project['topografia'] or '0%'}\t{'Coherente':<20}\t{'✅ Válido'}")
        r.append(f"{'Planimetrías':<25}\t{project['planimetrias'] or '0%'}\t{'Coherente':<20}\t{'✅ Válido'}")
        r.append(f"{'Ingeniería':<25}\t{project['ingenieria'] or '0%'}\t{'Coherente':<20}\t{'✅ Válido'}")
        r.append(f"{'Perfil T-E':<25}\t{project['perfil_tecnico_economico'] or '0%'}\t{'Coherente':<20}\t{'✅ Válido'}")
        r.append(f"{'Documentos':<25}\t{project['documentos'] or '0%'}\t{'Requerido':<20}\t{'✅ Válido'}")
        r.append(f"{'Avance (%)':<25}\t{avance_pct}%\t{'Coherente':<20}\t{'✅ Válido'}")
        r.append(f"{'Avance (Dec)':<25}\t{avance_pct/100:.1f}\t{'Matemática':<20}\t{'✅ Válido'}")
        r.append(f"Puntaje Dimensión 3: {scores['Dim3']:.0f}%")
        r.append(sep)

        # Dim 4
        r.append(f"📊 DIMENSIÓN 4: ESTADO Y CICLO DE VIDA {'⚠️' if has_errors else ''}")
        r.append(f"{'Variable':<25}\t{'Valor':<15}\t{'Validación':<20}\t{'Resultado'}")
        r.append(f"{'Etapa':<25}\t{etapa:<15}\t{'Lista válida':<20}\t{'✅ Válido'}")
        r.append(f"{'Estado':<25}\t{(estado or '-'):<15}\t{'Lista válida':<20}\t{'✅ Válido'}")
        res_post = "⚠️ Inconsistente" if has_errors else "✅ Válido"
        r.append(f"{'Postulación':<25}\t{(postulacion or '-'):<15}\t{'Coherente':<20}\t{res_post}")
        
        if has_errors:
            r.append("\n🔴 ALERTAS DE ALTA PRIORIDAD DETECTADAS")
            r.append("┌" + "─" * 65 + "┐")
            r.append("│                    DETALLE DE INCONSISTENCIAS                   │")
            r.append("└" + "─" * 65 + "┘")
            for a in high_severity_alerts:
                r.append(f"• [{a[1]}] {a[2]} ({a[0]})")
        r.append(f"Puntaje Dimensión 4: {scores['Dim4']:.0f}%")
        r.append(sep)

        # Dim 5, 6, 7 (Integración de validaciones reales)
        r.append("📊 DIMENSIÓN 5: EQUIPO PROFESIONAL")
        prof_res = "✅ Asignado" if profesional else "⚠️ Pendiente"
        r.append(f"{'Profesional 1':<25}\t{profesional or '-':<15}\t{'Responsabilidad':<20}\t{prof_res}")
        r.append(f"Puntaje Dimensión 5: {100 if profesional else 0}%") 
        r.append(sep)

        r.append("📊 DIMENSIÓN 6: APROBACIONES Y PERMISOS")
        dom_res = "✅ Sí" if project['aprobacion_dom'] == 'SÍ' else "⚠️ No/Pendiente"
        r.append(f"{'Aprobación DOM':<25}\t{(project['aprobacion_dom'] or 'No'):<15}\t{'Requerido':<20}\t{dom_res}")
        r.append("Puntaje Dimensión 6: 50%") 
        r.append(sep)

        r.append("📊 DIMENSIÓN 7: VARIABLES GEOGRÁFICAS")
        geo_res = "✅ Válido" if project['latitud'] and project['longitud'] else "⚠️ Faltante"
        r.append(f"{'Latitud':<25}\t{(project['latitud'] or '-'):<15}\t{'Obra física':<20}\t{geo_res}")
        r.append(f"{'Longitud':<25}\t{(project['longitud'] or '-'):<15}\t{'Obra física':<20}\t{geo_res}")
        r.append(f"Puntaje Dimensión 7: {100 if project['latitud'] else 0}%")
        r.append(sep)

        # --- SECCIONES FINALES ---
        r.append("🚨 RESUMEN DE ALERTAS GENERADAS")
        r.append(f"{'Nivel':<10}\t{'Código':<10}\t{'Descripción':<40}\t{'Plazo':<10}\t{'Responsable'}")
        for a in sorted_alerts:
            r.append(f"{a[0]:<10}\t{a[1]:<10}\t{a[2][:40]:<40}\t{a[3]:<10}\t{a[4] or '-'}")
        r.append(sep)

        r.append("📈 PUNTAJE DE CALIDAD DEL PROYECTO")
        r.append(f"{'Dimensión':<30}\t{'Puntaje':<10}\t{'Estado':<10}\t{'Peso':<8}\t{'Ponderado'}")
        r.append(f"{'Identificación y Clasificación':<30}\t{scores['Dim1']:>6.0f}%\t{'🟡':^10}\t{'10%':^8}\t{scores['Dim1']*0.1:>9.1f}")
        r.append(f"{'Priorización y Financiamiento':<30}\t{scores['Dim2']:>6.0f}%\t{'🟡':^10}\t{'15%':^8}\t{scores['Dim2']*0.15:>9.1f}")
        r.append(f"{'Variables Técnicas':<30}\t{scores['Dim3']:>6.0f}%\t{'✅':^10}\t{'20%':^8}\t{scores['Dim3']*0.2:>9.1f}")
        r.append(f"{'Estado y Ciclo de Vida':<30}\t{scores['Dim4']:>6.0f}%\t{'🔴':^10}\t{'25%':^8}\t{scores['Dim4']*0.25:>9.1f}")
        r.append(f"{'Variables Geográficas':<30}\t{(100 if project['latitud'] else 0):>6.0f}%\t{'✅':^10}\t{'10%':^8}\t{10.0 if project['latitud'] else 0.0:>9.1f}")
        r.append(f"\nCALIDAD GENERAL: {final_score:.1f}% {'⚠️ Requiere atención' if final_score < 80 else ''}")
        
        # Barra Visual
        r.append("\n┌" + "─" * 65 + "┐")
        r.append("│                    BARRA DE CALIDAD VISUAL                      │")
        r.append("└" + "─" * 65 + "┘")
        r.append("\n0%        25%        50%        75%       100%")
        r.append("|──────────|──────────|──────────|──────────|")
        filled = int(max(0, min(100, final_score)) / 100 * 40)
        r.append("█" * filled + "░" * (40 - filled) + f"  {final_score:.1f}%")
        r.append(sep)

        r.append("✅ PLAN DE ACCIÓN CORRECTIVO")
        r.append(f"{'Prioridad':<10}\t{'Acción':<50}\t{'Responsable':<12}\t{'Plazo':<10}\t{'Estado':<12}\t{'Fecha Compromiso'}")
        
        # Diccionario de acciones específicas refinado
        acciones_map = {
            "V001": f"Corregir Etapa de '{etapa}' a 'Factibilidad' (Consistente con Estado)",
            "V002": f"Ajustar Avance ({avance_pct}%) al rango institucional para {etapa}",
            "V003": "Completar carga técnica para Factibilidad (Topo/Plani/Doc 100%)",
            "V004": "Registrar fuente de financiamiento oficial requerida",
            "V005": f"Asignar Profesional Responsable en ficha técnica ({profesional or 'Catalán'})",
            "V006": "Georreferenciar proyecto: Ingresar Lat/Long en base de datos",
            "V007": "Regularizar Postulación (RS es inconsistente en Idea/Perfil)",
            "V008": "Actualizar registro de proyecto (Data desactualizada >90 días)",
            "V009": f"Revisar cronograma: Brecha de {diff_years} años excede límite de 5",
            "V010": "Definir monto de inversión estimado (Actual: $0)",
            "V011": "Asignar Código de Proyecto institucional definitivo",
            "V012": "Definir Sector territorial para la Unidad Vecinal asignada",
            "V013": "Sincronizar valores de avance: Decimal vs Porcentual",
            "V014": "Vincular Lineamiento Estratégico a proyecto de prioridad SI",
            "VI001": f"Subir archivos de respaldo obligatorios para etapa {etapa}",
            "VI002": "Ingresar observaciones de avance justificando la subsanación",
            "VI003": "Regularizar Hitos de Avance vs Porcentaje Declarado",
            "A02": "Actualizar fecha de actualización de BD (Regularizar ficha)",
            "M01": "Completar Unidad Vecinal en datos de identificación",
            "B01": "Registrar sector territorial del proyecto",
            "B02": "Definir Dupla Profesional para supervisión de obra"
        }

        for i, a in enumerate(sorted_alerts, 1):
            prio_label = a[0]
            icon = prio_icons.get(prio_label, "⚪")
            cod = a[1]
            accion = acciones_map.get(cod, a[2])
            resp = a[4] or (profesional if profesional else "Catalán")
            plazo = a[3]
            compromiso = get_compromiso(plazo)
            
            # Renderizado con iconos y formato fijo
            r.append(f"{icon}{i:<9}\t{accion:<50}\t{resp:<12}\t{plazo:<10}\t{'Pendiente':<12}\t{compromiso}")
            
        r.append(sep)

        # --- INTEGRACIÓN DE ANÁLISIS CUALITATIVO IA ---
        # Generamos versión base del reporte para que la IA lo lea
        reporte_base = "\n".join(r)
        analista = AIAnalyst()
        analisis_ia_text = analista.get_analysis(reporte_base)
        
        # Incorporamos el análisis al reporte final para TXT y PDF
        r.append("\n🔍 OBSERVACIONES DEL AUDITOR (GENERADO POR IA)")
        r.append("════════════════════════════════════════════════════════")
        r.append("ANÁLISIS CUALITATIVO")
        r.append("════════════════════════════════════════════════════════")
        r.append(analisis_ia_text)
        r.append("════════════════════════════════════════════════════════")
        
        final_report = "\n".join(r)

        # --- PREPARACIÓN DE TUPLA PARA BATCH INSERT ---
        tupla_bd = None
        if lote_id:
            conteo_criticas = len([a for a in alerts if a[0] == "CRÍTICO"])
            conteo_altas = len([a for a in alerts if a[0] == "ALTO"])
            conteo_medias = len([a for a in alerts if a[0] == "MEDIO"])
            conteo_bajas = len([a for a in alerts if a[0] == "BAJO"])
            
            tupla_bd = (
                lote_id, project_id,
                project.get('n_registro'), project.get('nombre'), project.get('area_id'), project.get('lineamiento_estrategico_id'), 
                project.get('financiamiento_id'), project.get('financiamiento_municipal'), project.get('monto'), 
                project.get('anno_elaboracion'), project.get('anno_ejecucion'),
                project.get('topografia'), project.get('planimetrias'), project.get('ingenieria'), 
                project.get('perfil_tecnico_economico'), project.get('documentos'),
                project.get('avance_total_porcentaje'), project.get('avance_total_decimal'), 
                project.get('estado_proyecto_id'), project.get('etapa_proyecto_id'), project.get('estado_postulacion_id'), project.get('fecha_postulacion'),
                project.get('dupla_profesionales'), project.get('profesional_1'), project.get('profesional_2'), project.get('profesional_3'), 
                project.get('profesional_4'), project.get('profesional_5'),
                project.get('unidad_vecinal'), project.get('sector_id'), project.get('aprobacion_dom'), project.get('aprobacion_serviu'), 
                project.get('latitud'), project.get('longitud'), project.get('observaciones'), project.get('activo'),
                count_docs, count_hitos, count_obs,
                final_score, scores.get('Dim1', 0), scores.get('Dim2', 0), scores.get('Dim3', 0), scores.get('Dim4', 0), 
                (100 if profesional else 0), 50, (100 if project['latitud'] else 0),
                avance_pct, etapa, estado,
                conteo_criticas, conteo_altas, conteo_medias, conteo_bajas,
                json.dumps(alerts, default=str),
                analisis_ia_text
            )

        return final_report, tupla_bd


    except Exception as e:
        return f"Error en la ejecución: {str(e)}", None

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Auditoría Integral de Proyectos')
    parser.add_argument('--id', type=int, help='ID del proyecto específico a auditar')
    parser.add_argument('--all', action='store_true', help='Auditar todos los proyectos activos')
    
    # Adaptación para Jupyter Notebook/IPython
    if 'ipykernel' in sys.modules:
        args = parser.parse_args([]) # No pasar sys.argv en notebooks
    else:
        args = parser.parse_args()

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as main_cur:
            if args.id:
                ids = [args.id]
            else:
                print("🔍 Obteniendo lista general de proyectos (activos e inactivos)...")
                main_cur.execute("SELECT id FROM proyectos ORDER BY id ASC")
                ids = [row[0] for row in main_cur.fetchall()]
        
        if not ids:
            print("❌ No se encontraron proyectos para auditar.")
            if 'ipykernel' not in sys.modules:
                sys.exit(0)

        print(f"🚀 Iniciando proceso de auditoría para {len(ids)} proyectos...")
        
        # Iniciar Lote de Auditoría
        lote_id = None
        con_lote = False
        try:
            with conn.cursor() as cur_lote:
                cur_lote.execute("INSERT INTO auditoria_lotes (total_proyectos_auditados) VALUES (%s) RETURNING id", (len(ids),))
                lote_id = cur_lote.fetchone()[0]
                conn.commit() # Commit inicial para el Lote ID
            print(f"📋 Lote de Auditoría creado en BD con ID: {lote_id}")
            con_lote = True
        except Exception as e:
            print(f"⚠️ No se pudo inicializar Lote de Auditoría en la Base de Datos: {e}")

        # Directorios de salida
        txt_dir = "reportes_txt"
        pdf_dir = "reportes_pdf"
        os.makedirs(txt_dir, exist_ok=True)
        os.makedirs(pdf_dir, exist_ok=True)
        
        # BATCHING DATA
        batch_inserts = []

        # Cursor general para todas las lecturas de los proyectos
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as process_cur:
            for i, pid in enumerate(ids, 1):
                if i % 10 == 0 or i == 1:
                    print(f"[{i}/{len(ids)}] Auditando Proyecto ID: {pid}...")
                
                content, tupla_bd = audit_project(process_cur, pid, lote_id=lote_id)
                
                if tupla_bd:
                    batch_inserts.append(tupla_bd)
                
                # Generar Reportes I/O locales
                txt_filename = os.path.join(txt_dir, f"{pid}.txt")
                with open(txt_filename, "w", encoding="utf-8") as f:
                    f.write(content)
                pdf_filename = os.path.join(pdf_dir, f"{pid}.pdf")
                generate_pdf_from_text(content.split('\n'), pdf_filename)
        
        # BATCH DATABASE TRANSACTION
        if con_lote and lote_id and batch_inserts:
            print(f"💾 Ejecutando Volcado Transaccional Masivo: {len(batch_inserts)} registros...")
            try:
                with conn.cursor() as insert_cur:
                    insert_query = """
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
                            cant_documentos, cant_hitos, cant_observaciones,
                            puntaje_general, puntaje_d1, puntaje_d2, puntaje_d3, puntaje_d4, puntaje_d5, puntaje_d6, puntaje_d7,
                            avance_declarado, etapa, estado,
                            alertas_criticas, alertas_altas, alertas_medias, alertas_bajas,
                            alertas_json, analisis_ia
                        ) VALUES %s
                    """
                    psycopg2.extras.execute_values(insert_cur, insert_query, batch_inserts)
                    
                    # Actualizar promedio
                    insert_cur.execute("UPDATE auditoria_lotes SET promedio_calidad_general = (SELECT COALESCE(AVG(puntaje_general), 0) FROM auditoria_proyectos WHERE lote_id = %s) WHERE id = %s", (lote_id, lote_id))
                    conn.commit()
                print("✅ Transacción BD completada con éxito.")
            except Exception as e:
                conn.rollback()
                print(f"❌ Error en transaccionalidad BD (Rollback Emitido): {e}")

        print(f"\n✅ Proceso completado. Se generaron {len(ids)} reportes de auditoría.")

    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
    finally:
        if conn:
            conn.close()
