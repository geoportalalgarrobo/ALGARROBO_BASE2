# Stack Tecnológico Detallado

## Resumen del Stack
El proyecto **Geoportal Municipal - Algarrobo** es una plataforma Web Fullstack de grado gubernamental diseñada para la gestión territorial y administrativa. El código se gestiona íntegramente en **GitHub**, siguiendo un modelo de desarrollo modular. La arquitectura se divide en un frontend estático de alto rendimiento servido por **GitHub Pages** y un ecosistema de backend en Python (Flask) desplegado en **Railway**. La persistencia se delega a **Neon**, una base de datos PostgreSQL serverless que permite un escalado elástico y una gestión de conexiones optimizada para entornos cloud.

---

## Frontend: Arquitectura y Diseño
El frontend ha sido diseñado bajo la premisa de "Zero Framework Overhead", utilizando tecnologías nativas para maximizar la velocidad de carga y la compatibilidad con navegadores institucionales.

| Tecnología | Versión | Rol en el Proyecto | Implementación |
|---|---|---|---|
| **HTML5 / JavaScript** | Vanilla | Lógica de componentes y ruteo | Utiliza el patrón de "Page Controller" para manejar la lógica de cada vista de forma independiente en `frontend/script/`. |
| **Tailwind CSS** | 3.x (CDN) | Diseño y Layout | Implementa un sistema de diseño basado en utilidades para mantener la consistencia visual sin necesidad de archivos CSS pesados. |
| **Outfit (Google Fonts)** | N/A | Tipografía | Fuente moderna de tipo sans-serif que mejora la legibilidad en mapas y dashboards técnicos. |
| **Font Awesome** | 6.4.0 | Iconografía | Provee el set visual para la navegación y estados de los proyectos. |

### Componentes Críticos del Frontend:
- **Auto-Routing (`router.js`)**: Un script inteligente que detecta el `hostname` del navegador. Si detecta `github.io`, ajusta dinámicamente el `BASE_PATH` para evitar errores de ruta 404 en el entorno de producción.
- **Gestión de Sesiones**: Implementa un sistema de validación basado en tokens almacenados en `localStorage`. El middleware de cliente redirige automáticamente al login si detecta la ausencia de credenciales válidas.
- **API Wrapper (`api.js`)**: Centraliza todas las peticiones hacia el backend, manejando automáticamente las cabeceras de `Authorization: Bearer <token>` y el parseo de errores.

---

## Backend: Procesamiento y Lógica de Negocio
El backend es el motor de procesamiento del sistema, manejando desde la autenticación hasta el procesamiento OCR de documentos legales.

| Tecnología | Versión | Rol en el Proyecto | Necesidad Técnica |
|---|---|---|---|
| **Flask** | 3.0.0 | API RESTful | Elegido por su ligereza y facilidad para integrar librerías de procesamiento de datos en Python. |
| **Gunicorn** | 21.2.0 | Servidor WSGI | Gestiona múltiples workers para manejar peticiones simultáneas en el entorno de Railway. |
| **PyPDF2** | 3.0.1 | Extracción de PDF | Permite la lectura programática de decretos y resoluciones municipales en formato PDF nativo. |
| **Python-docx** | 1.1.0 | Procesamiento Word | Crucial para la lectura de minutas y borradores administrativos cargados por los usuarios. |
| **Pytesseract** | 0.3.10 | Motor de OCR | Interfaz para Tesseract OCR que permite "leer" documentos escaneados o imágenes de planos. |
| **Bcrypt** | 4.1.2 | Seguridad | Implementa el algoritmo Blowfish para el hasheo de contraseñas, garantizando protección contra ataques de fuerza bruta. |

### Pipeline de Procesamiento de Documentos (`extract.py`):
El sistema implementa un flujo de tres capas para la extracción de información:
1.  **Capa Nativa**: Intenta extraer texto directamente si el archivo es un PDF digital o un `docx`.
2.  **Capa de Conversión**: Utiliza **LibreOffice (soffice)** en modo `headless` para convertir archivos `.doc` antiguos o formatos complejos a texto plano indexable.
3.  **Capa OCR**: Si el archivo es una imagen (`png`, `jpg`), se procesa a través de **Tesseract** para recuperar el texto contenido.

---

## Base de Datos y Gestión de Persistencia
El sistema utiliza **Neon**, que provee una infraestructura de PostgreSQL serverless sobre AWS.

### Optimización de Conexiones (`neon.py` / `app21.py`):
Dado que Neon puede desconectar conexiones inactivas para ahorrar recursos (idle mode), el backend implementa:
- **ThreadedConnectionPool**: Un pool de conexiones que mantiene entre 2 y 10 enlaces activos.
- **Health Check Worker**: Un hilo de ejecución en segundo plano que cada 30 segundos verifica la salud de la conexión y realiza una consulta de "keep-alive" (`SELECT 1`).
- **Auto-Reinstatment**: En caso de fallo de red, el pool se destruye y se recrea de forma transparente para el usuario final.

---

## Infraestructura y Servicios Externos
| Plataforma | Propósito | Detalles Técnicos |
|---|---|---|
| **GitHub** | Código Fuente | Gestión de versiones y colaboración. |
| **GitHub Pages** | Hosting UI | Despliegue automático de la carpeta `frontend/`. |
| **Railway** | Hosting API | Despliegue basado en el `Dockerfile` raíz. |
| **Brevo** | SMTP Relay | Utilizado para el envío de alertas de auditoría y reportes PDF vía email. |
| **Tesseract OCR** | Binario de Sistema | Motor externo instalado en el contenedor Docker para el procesamiento de imágenes. |
| **LibreOffice** | Binario de Sistema | Utilizado para la interoperabilidad entre formatos de Microsoft Office y texto plano. |

---

## Seguridad y Auditoría
El sistema cumple con estándares de auditoría municipal:
- **Módulo de Auditoría Técnica**: Cada vez que un usuario modifica un proyecto o sube un documento, se registra en la tabla `control_actividad` el usuario, la acción, el IP de origen, el User-Agent y los datos (antes/después) en formato JSON.
- **Sesiones Expirables**: Las sesiones se gestionan en memoria con un tiempo de vida de 1 hora de inactividad, tras lo cual el token es invalidado por el servidor.
- **RLock de Conexión**: Se utiliza `threading.RLock` para evitar condiciones de carrera (*race conditions*) durante el acceso simultáneo a la base de datos por múltiples hilos de la API.

> ⚠️ **Nota de Verificación**: La integración con LibreOffice requiere que el binario `soffice` esté correctamente configurado en el PATH o definido en la variable `SOFFICE_PATH` del entorno.
