import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import json

# ==============================================================================
# SCRIPT DE AUDITORÍA HISTÓRICA DE PROYECTOS (verificador2.py)
# Genera Reporte Estructurado de Avances y Cambios (PDF y TXT)
# ==============================================================================

# NOTA: Configura tu cadena de conexión
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

def generate_pdf_from_text(lines, filename):
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

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
                            txt_style = normal_bold if len(str(cell)) < 30 and ("⚠️" in str(cell) or "🔴" in str(cell) or "CRÍTICO" in str(cell)) else styles['Normal']
                            formatted_row.append(Paragraph(str(cell).strip(), txt_style))
                    formatted_data.append(formatted_row)
                
                cols = len(current_table_data[0])
                header_text = " ".join(current_table_data[0]).upper()
                colWidths = None
                
                if cols == 2: colWidths = [4*cm, 22*cm]
                elif cols == 3: colWidths = [5*cm, 5*cm, 16*cm]
                elif cols == 4: colWidths = [4.5*cm, 4.5*cm, 6*cm, 11*cm]
                elif cols == 5: colWidths = [4*cm, 3*cm, 4*cm, 3.5*cm, 11.5*cm]
                elif cols == 6: colWidths = [4*cm, 3.5*cm, 3.5*cm, 3*cm, 3*cm, 9*cm]
                
                t = Table(formatted_data, colWidths=colWidths)
                
                header_bg = colors.HexColor('#4f46e5')
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
            
            if not line or set(line).issubset({'_', '═', '─', '┌', '┐', '└', '┘', '│', '█', '░', '|'}):
                commit_table()
                continue
                
            if '\t' in original_line:
                current_table_data.append([c.strip() for c in original_line.split('\t')])
            else:
                commit_table()
                if line.startswith("📋"):
                    story.append(Paragraph(line, title_style))
                elif line.startswith("ID DEL PROYECTO"):
                    story.append(Paragraph(line, sub_style))
                elif line.startswith("📊") or line.startswith("📈") or line.startswith("🕒"):
                    story.append(Paragraph(line, h2_style))
                    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#4f46e5')))
                    story.append(Spacer(1, 0.2*cm))
                else:
                    story.append(Paragraph(line, normal_style))
                    story.append(Spacer(1, 0.1*cm))
                    
        commit_table()
        doc.build(story)
        return True
    except Exception as e:
        print(f"Error generando PDF para {filename}: {str(e)}")
        return False

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def process_project_history(cur, project_id):
    try:
        # Obtener información básica del proyecto
        cur.execute("SELECT n_registro, nombre FROM proyectos WHERE id = %s", (project_id,))
        project = cur.fetchone()
        if not project:
            return f"Error: Proyecto ID {project_id} no encontrado."

        r = []
        sep = "─" * 80
        
        r.append(f"📋 REPORTE DE HISTORIAL Y AVANCES DEL PROYECTO")
        r.append(f"ID DEL PROYECTO: {project_id} | CÓDIGO: {project.get('n_registro') or 'N/A'}")
        r.append(f"NOMBRE: {project.get('nombre') or 'Sin Nombre'}")
        r.append(sep)

        # 1. Obtener avances desde auditoria_proyectos
        cur.execute("""
            SELECT al.fecha_ejecucion, ap.avance_declarado, ap.etapa, ap.estado, ap.puntaje_general, ap.alertas_criticas
            FROM auditoria_proyectos ap
            JOIN auditoria_lotes al ON ap.lote_id = al.id
            WHERE ap.proyecto_id = %s
            ORDER BY al.fecha_ejecucion DESC
        """, (project_id,))
        auditorias = cur.fetchall()

        r.append("📈 SECUENCIA DE AVANCES Y REVISIONES (Desde Snapshot Auditoría)")
        if not auditorias:
            r.append("No hay registros de auditoría para este proyecto.")
        else:
            r.append(f"{'Fecha Auditoría':<20}\t{'Avance %':<12}\t{'Etapa':<20}\t{'Estado':<20}\t{'Puntaje':<10}\t{'Alertas Críticas'}")
            for aud in auditorias:
                fecha = aud['fecha_ejecucion'].strftime("%Y-%m-%d %H:%M") if aud['fecha_ejecucion'] else "-"
                avance = f"{aud['avance_declarado']}%" if aud['avance_declarado'] is not None else "-"
                etapa = str(aud['etapa'] or "-")[:20]
                estado = str(aud['estado'] or "-")[:20]
                puntaje = f"{aud['puntaje_general']}%" if aud['puntaje_general'] is not None else "-"
                crit = str(aud['alertas_criticas'] or "0")
                r.append(f"{fecha:<20}\t{avance:<12}\t{etapa:<20}\t{estado:<20}\t{puntaje:<10}\t{crit}")
        r.append(sep)

        # 2. Obtener historial detallado de cambios (desde control_actividad)
        cur.execute("""
            SELECT c.fecha, c.accion, u.nombre as autor, c.detalle, c.datos_antes, c.datos_despues
            FROM control_actividad c
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE c.entidad_tipo = 'proyecto' AND c.entidad_id = %s
            ORDER BY c.fecha DESC
        """, (project_id,))
        historial = cur.fetchall()

        r.append("🕒 HISTORIAL COMPLETO DE ACCIONES Y CAMBIOS DEL PROYECTO")
        if not historial:
            r.append("No hay registros de actividad/cambios para este proyecto.")
        else:
            r.append(f"{'Fecha':<16}\t{'Acción':<20}\t{'Autor':<20}\t{'Detalle / Cambios'}")
            for h in historial:
                fecha = h['fecha'].strftime("%Y-%m-%d %H:%M") if h['fecha'] else "-"
                accion = str(h['accion'])[:20]
                autor = str(h['autor'] or "Sistema")[:20]
                
                # Resumir el cambio
                detalle = h['detalle'] or ""
                if h['accion'] == 'editar_proyecto':
                    antes = h['datos_antes'] or {}
                    despues = h['datos_despues'] or {}
                    if isinstance(antes, str): antes = json.loads(antes)
                    if isinstance(despues, str): despues = json.loads(despues)
                    
                    cambios = []
                    for k, v in despues.items():
                        v_antes = antes.get(k)
                        if str(v) != str(v_antes) and k not in ['fecha_actualizacion', 'actualizado_por']:
                            cambios.append(f"{k}: {v_antes} -> {v}")
                    if cambios:
                        detalle = "Campos Modificados: " + ", ".join(cambios)
                        if len(detalle) > 100:
                            detalle = detalle[:97] + "..."
                    else:
                        detalle = "Sin cambios detectables en campos auditables."
                        
                r.append(f"{fecha:<16}\t{accion:<20}\t{autor:<20}\t{detalle}")
        
        r.append(sep)
        return "\n".join(r)

    except Exception as e:
        return f"Error en la extracción para proyecto {project_id}: {str(e)}"

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Historial de Proyectos')
    parser.add_argument('--id', type=int, help='ID del proyecto específico a consultar')

    if 'ipykernel' in sys.modules:
        args = parser.parse_args([])
    else:
        args = parser.parse_args()

    # Si estamos en un entorno donde DATABASE_URL está en backend/.env_neon
    # Intentamos leerlo por defecto si no está definido en os.environ
    if "postgres" not in DATABASE_URL:
        # Fallback (puede obviarse si la URL está bien configurada globalmente)
        DATABASE_URL = "postgres://postgres:postgres@localhost:5432/algarrobo_db"

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as main_cur:
            if args.id:
                ids = [args.id]
            else:
                print("🔍 Obteniendo lista general de proyectos...")
                main_cur.execute("SELECT id FROM proyectos ORDER BY id ASC")
                ids = [row[0] for row in main_cur.fetchall()]
        
        if not ids:
            print("❌ No se encontraron proyectos.")
            sys.exit(0)

        # Directorios de salida requeridos
        txt_dir = "reportes2_txt"
        pdf_dir = "reportes2_pdf"
        os.makedirs(txt_dir, exist_ok=True)
        os.makedirs(pdf_dir, exist_ok=True)

        for i, pid in enumerate(ids, 1):
            if i % 10 == 0 or i == 1:
                print(f"[{i}/{len(ids)}] Procesando historial para Proyecto ID: {pid}...")
            
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                content = process_project_history(cur, pid)
                
            if not content.startswith("Error"):
                txt_filename = os.path.join(txt_dir, f"{pid}_historial.txt")
                with open(txt_filename, "w", encoding="utf-8") as f:
                    f.write(content)
                
                pdf_filename = os.path.join(pdf_dir, f"{pid}_historial.pdf")
                generate_pdf_from_text(content.split('\n'), pdf_filename)
        
        print(f"\n✅ Proceso completado. Se generaron {len(ids)} historiales (TXT y PDF).")

    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
    finally:
        if conn:
            conn.close()
