# Guía de Instalación y Configuración Local Detallada

Esta guía proporciona los pasos necesarios para desplegar un entorno de desarrollo completo para el **Geoportal Municipal - Algarrobo**. El proceso abarca la configuración de la base de datos cloud, la instalación de binarios del sistema para procesamiento de archivos y la puesta en marcha de los servidores de backend y frontend.

---

## 1. Requisitos Previos del Sistema

El proyecto depende de herramientas externas que deben estar instaladas en el sistema operativo anfitrión.

### A. Python 3.11+
El backend está escrito íntegramente en Python 3.11. Asegúrate de tenerlo instalado y accesible desde el PATH de tu sistema.
- **Windows**: Descarga el instalador de `python.org` y marca la opción "Add Python to PATH".
- **Debian/Ubuntu**: `sudo apt update && sudo apt install python3 python3-pip python3-venv`

### B. Tesseract OCR (Binario de Sistema)
Necesario para la extracción de texto de imágenes (`extract.py`).
- **Windows**: Descarga el instalador de `UB Mannheim` y toma nota de la ruta de instalación (por defecto `C:\Program Files\Tesseract-OCR`). Añade esta ruta a las variables de entorno del sistema.
- **Debian/Ubuntu**: `sudo apt install tesseract-ocr tesseract-ocr-spa` (Instalar paquete de español para mejorar la precisión).

### C. LibreOffice (Binario de Sistema)
Utilizado para convertir documentos `.doc` antiguos y otros formatos a texto plano.
- **Windows**: Instala LibreOffice desde `libreoffice.org`. La ruta por defecto será `C:\Program Files\LibreOffice\program\soffice.exe`.
- **Debian/Ubuntu**: `sudo apt install libreoffice-writer libreoffice-calc`

### D. PostgreSQL
Se recomienda usar **Neon.tech** por su compatibilidad nativa con las herramientas de pooling del proyecto. Si usas un PostgreSQL local, asegúrate de que sea versión 15 o superior.

---

## 2. Clonación y Estructura inicial

```bash
# Clonar el código fuente
git clone https://github.com/Sud-Austral/ALGARROBO_BASE2.git
cd ALGARROBO_BASE2

# Crear un entorno virtual para aislar las dependencias del backend
cd backend
python -m venv venv

# Activar el entorno virtual
# En Windows:
.\venv\Scripts\activate
# En Linux/Unix:
source venv/bin/activate
```

---

## 3. Instalación de Dependencias de Python

Instala los paquetes necesarios definidos en `requirements.txt`. Estos incluyen Flask, adaptadores de DB y librerías de procesamiento de archivos.

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Configuración de Base de Datos y Variables de Entorno

Crea un archivo `.env` en la raíz de la carpeta `/backend/`. Puedes basarte en el siguiente esquema, completando con tus credenciales reales:

```env
# Conexión Base de Datos (Neon o Postgres Local)
DATABASE_URL="postgresql://usuario:password@host/nombre_db?sslmode=require"

# Configuración Servidor
PORT=8000
FLASK_DEBUG=True

# Configuración de Correo (SMTP Relay vía Brevo)
BREVO_SMTP_LOGIN="tu_usuario@smtp-brevo.com"
BREVO_SMTP_KEY="tu_clave_api_x_smtp_sib"
REMITENTE="geoportal.algarrobo@gmail.com"
REPLY_TO="geoportal.algarrobo@gmail.com"

# Rutas de Binarios (Opcional si están en el PATH)
SOFFICE_PATH="C:\Program Files\LibreOffice\program\soffice.exe"
```

---

## 5. Inicialización de la Base de Datos

El backend cuenta con una función de **auto-sembrado** (`ensure_tables` en `app21.py` o `neon.py`) que crea las tablas necesarias al arrancar por primera vez.

1. Asegúrate de que `DATABASE_URL` apunte a una base de datos vacía pero accesible.
2. Inicia el servidor (ver sección 6); las tablas `users`, `divisiones`, `roles`, `proyectos`, etc., se crearán automáticamente.
3. Se sembrarán los 32 pasos estándar del workflow de licitaciones en la tabla `licitacion_pasos_maestro`.

**Creación manual (Opcional):**
Si prefieres ejecutar los scripts manualmente para auditoría, utiliza el archivo `database/database.sql` y `database/licitaciones.sql`.

---

## 6. Ejecución de los Servidores

### Backend (Desarrollo)
```bash
python app21.py
```
🚀 Verás el log: `Backend Municipal iniciando...`. El servidor estará escuchando en `http://localhost:8000`.

### Frontend (Servidor Estático)
Al ser una aplicación Vanilla JS, no hay un proceso de build. Solo necesitas servir la carpeta `frontend/`.
- **VS Code**: Usa la extensión `Live Server` sobre `frontend/index.html`.
- **Python**: `python -m http.server 8080` (dentro de la carpeta `frontend/`).
- **Node**: `npx serve frontend` (desde la raíz).

---

## 7. Verificación Técnica de la Instalación

Para confirmar que el sistema está 100% operativo, realiza estas tres pruebas:

1.  **Conexión API**: Abre `http://localhost:8000/health` en tu navegador. Deberías ver un JSON con `"status": "healthy"` y detalles del pool de conexiones.
2.  **Acceso UI**: Abre el navegador en la URL del servidor estático. La página de login debe cargar correctamente y el sistema de ruteo debe detectar tu URL base.
3.  **Logs**: Revisa el archivo `municipal_api.log` en el directorio backend para detectar posibles errores de conexión inicial con Neon.

---

## 8. Solución de Problemas (Troubleshooting)

### Error: `Pool de conexiones fallido`
- **Causa**: NeonDB cierra conexiones inactivas o hay un error de SSL.
- **Solución**: Asegúrate de incluir `?sslmode=require` al final de tu `DATABASE_URL`. El código de `neon.py` intentará reconectar automáticamente con un esquema de reintentos exponenciales.

### Error: `soffice no generó ningún .txt`
- **Causa**: El backend no encuentra el ejecutable de LibreOffice para convertir documentos `.doc`.
- **Solución**: Verifica que la ruta en `SOFFICE_PATH` sea exacta o añade el directorio `program` de LibreOffice al PATH del sistema.

### Error: `404 Not Found` al navegar en GitHub Pages
- **Causa**: Las rutas dentro de la aplicación no coinciden con la URL del repositorio.
- **Solución**: El archivo `frontend/script/router.js` tiene lógica de auto-detección para GitHub. Asegúrate de que tu repositorio en GitHub se llame exactamente como el path configurado (`/ALGARROBO_BASE2`).

### Error: `ModuleNotFoundError: No module named 'psycopg2'`
- **Causa**: El entorno virtual no está activo o falló la instalación del adaptador de Postgres.
- **Solución**: Activa el entorno virtual con `source venv/bin/activate` y ejecuta `pip install psycopg2-binary`.

---

## 9. Despliegue con Docker (Opcional)

Si deseas simular el entorno de producción (Railway) localmente:

```bash
cd backend
# Construir imagen
docker build -t geoportal-backend .
# Ejecutar enviando las variables de entorno
docker run -p 8000:8000 --env-file .env geoportal-backend
```
El contenedor docker ya incluye internamente las instalaciones de Tesseract y LibreOffice optimizadas para Linux Slim.
