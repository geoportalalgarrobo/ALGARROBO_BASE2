import os
import re
import json
import smtplib
import email.utils
import logging
import unicodedata
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Configuración de Logging
logger = logging.getLogger(__name__)

def normalize_text(text):
    """Elimina acentos y convierte a minúsculas para comparaciones robustas."""
    if not text:
        return ""
    text = str(text)
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()

def get_email_config():
    """Obtiene la configuración de correo desde el entorno."""
    # Asegurar que las variables estén cargadas
    load_dotenv()
    return {
        "login": os.getenv("BREVO_SMTP_LOGIN"),
        "key": os.getenv("BREVO_SMTP_KEY"),
        "remitente": os.getenv("REMITENTE", "geoportal.algarrobo@gmail.com"),
        "reply_to": os.getenv("REPLY_TO", "geoportal.algarrobo@gmail.com")
    }

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_CORREO_PATH = os.path.join(BASE_DIR, "config_correo.json")

def obtener_correos_responsables(responsables_list):
    """
    Busca los correos electrónicos para una lista de nombres o apellidos
    en el archivo config_correo.json usando normalización de acentos.
    """
    try:
        if not os.path.exists(CONFIG_CORREO_PATH):
            logger.error(f"No se encontró el archivo de configuración: {CONFIG_CORREO_PATH}")
            return []

        with open(CONFIG_CORREO_PATH, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        # Normalizar las llaves del JSON de configuración
        norm_mapping = {normalize_text(k): v for k, v in mapping.items()}

        correos = []
        for nombre in responsables_list:
            if not nombre or str(nombre).strip() == "":
                continue
            
            nombre_norm = normalize_text(nombre)
            logger.info(f"Buscando correo para: {nombre} (normalizado: {nombre_norm})")
            
            encontrado = False
            # Búsqueda por coincidencia
            for key_norm, email_val in norm_mapping.items():
                if key_norm in nombre_norm:
                    correos.append(email_val)
                    encontrado = True
                    logger.info(f"¡Match encontrado! {key_norm} -> {email_val}")
                    break 
            
            if not encontrado:
                logger.warning(f"No se encontró correo para el responsable: {nombre}")

        # Eliminar duplicados
        unique_emails = list(set(correos))
        return unique_emails
    except Exception as e:
        logger.error(f"Error cargando correos responsables: {e}")
        return []

def construir_mensaje(destinatarios_list, ruta_pdf, proyecto_id, proyecto_nombre=""):
    """
    Construye el objeto MIMEMultipart con el PDF adjunto.
    """
    config = get_email_config()
    
    if not os.path.exists(ruta_pdf):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_pdf}")

    nombre_archivo = os.path.basename(ruta_pdf)
    asunto = f"Reporte de Auditoría Técnica - Proyecto N° {proyecto_id}"
    if proyecto_nombre:
        asunto += f" - {proyecto_nombre}"

    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
      <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #4f46e5; color: white; padding: 20px; text-align: center;">
          <h2 style="margin: 0;">Informe de Auditoría Técnica</h2>
        </div>
        <div style="padding: 30px;">
          <p>Estimados responsables,</p>
          <p>Adjunto encontrarán el <strong>Informe de Auditoría Técnica</strong> correspondiente
             al proyecto número <strong>{proyecto_id}</strong>: <em>{proyecto_nombre}</em>.</p>
          <p>Este documento contiene los indicadores de cumplimiento actualizados y las alertas detectadas por el Sistema Geoportal Algarrobo.</p>
          
          <div style="background-color: #f8fafc; border-left: 4px solid #4f46e5; padding: 15px; margin: 20px 0;">
            <strong>Detalles del Envío:</strong><br>
            ID Proyecto: {proyecto_id}<br>
            Fecha: {email.utils.formatdate(localtime=True)}
          </div>

          <p>Se solicita revisar las observaciones y priorizar las correcciones indicadas en el plan de acción del PDF adjunto.</p>
          
          <p>Atentamente,<br>
          <span style="color: #4f46e5; font-weight: bold;">Unidad de Planificación y Control</span><br>
          Municipalidad de Algarrobo</p>
        </div>
        <div style="background-color: #f1f5f9; padding: 15px; font-size: 11px; color: #64748b; text-align: center;">
          <hr style="border: 0; border-top: 1px solid #cbd5e1; margin-bottom: 10px;">
          <p>
            AVISO DE CONFIDENCIALIDAD: Este mensaje va dirigido exclusivamente a su destinatario.
            Si lo recibiera por error, comuníquelo al remitente y elimínelo de inmediato.
          </p>
        </div>
      </div>
    </body>
    </html>
    """

    cuerpo_texto = (
        f"Estimados responsables,\n\n"
        f"Adjunto encontrarán el Informe de Auditoría Técnica del proyecto N° {proyecto_id}: {proyecto_nombre}.\n\n"
        f"Este documento contiene los indicadores de cumplimiento actualizados a la fecha y alertas detectadas.\n\n"
        f"Atentamente,\n"
        f"Unidad de Planificación y Control\n"
        f"Municipalidad de Algarrobo"
    )

    msg = MIMEMultipart("mixed")
    msg["From"]       = f"Geoportal Algarrobo <{config['remitente']}>"
    msg["Reply-To"]   = config['reply_to']
    msg["To"]         = ", ".join(destinatarios_list)
    msg["Subject"]    = asunto
    msg["Date"]       = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="gmail.com")

    alternativo = MIMEMultipart("alternative")
    alternativo.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
    alternativo.attach(MIMEText(cuerpo_html,  "html",  "utf-8"))
    msg.attach(alternativo)

    try:
        with open(ruta_pdf, "rb") as f:
            adjunto = MIMEBase("application", "pdf")
            adjunto.set_payload(f.read())
        encoders.encode_base64(adjunto)
        adjunto.add_header("Content-Disposition", f'attachment; filename="{nombre_archivo}"')
        msg.attach(adjunto)
    except Exception as e:
        logger.error(f"Error adjuntando PDF: {e}")
        raise e

    return msg

def enviar_email_responsables(proyecto_id, responsables_names, ruta_pdf, proyecto_nombre=""):
    """
    Función principal para enviar el correo a los responsables mapeados.
    """
    config = get_email_config()
    destinatarios = obtener_correos_responsables(responsables_names)
    
    if not destinatarios:
        return {"success": False, "message": "No se encontraron correos configurados para los responsables asignados."}

    if not config["login"] or not config["key"]:
        return {"success": False, "message": "Faltan credenciales de SMTP (BREVO_SMTP_LOGIN/KEY) en el entorno."}

    try:
        msg = construir_mensaje(destinatarios, ruta_pdf, proyecto_id, proyecto_nombre)
        
        logger.info(f"Iniciando sesión en Brevo SMTP para enviar a {len(destinatarios)} destinatarios...")
        with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(config["login"], config["key"])
            server.sendmail(config["remitente"], destinatarios, msg.as_string())
            
        logger.info(f"✅ ¡Éxito! Correo enviado para proyecto {proyecto_id}")
        return {
            "success": True, 
            "message": f"Correo enviado exitosamente a: {', '.join(destinatarios)}",
            "enviados": destinatarios
        }

    except Exception as e:
        error_msg = f"Error enviando correo: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg}

