# INFORME TÉCNICO DE AUDITORÍA DE CÓDIGO FUENTE
## Geoportal Municipal — Municipalidad de Algarrobo
### Departamento de Informática — SECPLAC

---

**Clasificación:** Uso Interno Restringido  
**Fecha de emisión:** 30 de marzo de 2026  
**Repositorio auditado:** `github.com/geoportalalgarrobo/ALGARROBO_BASE2`  
**Versión del sistema:** 2.0.0 (según `backend/app21.py`)  
**Auditor:** Departamento de Informática Municipal  

---

## 1. RESUMEN EJECUTIVO

El presente informe documenta los resultados de la auditoría técnica de código fuente del "Geoportal Municipal", plataforma web encargada por SECPLAC para la gestión interna de proyectos de la Municipalidad de Algarrobo.

El análisis revela que el sistema presenta **vulnerabilidades de severidad crítica que impiden su recepción conforme en el estado actual**. En particular, se identificaron credenciales de acceso a la base de datos de producción expuestas públicamente en el repositorio, tres endpoints administrativos de alta sensibilidad completamente desprotegidos (que permiten la descarga y sobreescritura de todo el contenido del servidor sin autenticación), y una ausencia generalizada de control de autorización por rol en el backend, lo que significa que cualquier usuario autenticado puede ejecutar operaciones reservadas a administradores.

Adicionalmente, se detectan deficiencias en el modo de depuración activado por defecto, filtración de información técnica sensible, y la presencia de módulos fuera del alcance contractual cuya inclusión no fue declarada al mandante.

El sistema **no se encuentra en condiciones de ser recepcionado ni puesto en producción** hasta que los hallazgos categorizados como "Bloqueante" sean corregidos y verificados por el Departamento de Informática.

---

### Tabla Resumen de Hallazgos

| N° | Hallazgo | Prioridad |
|----|----------|-----------|
| H-01 | Credenciales de base de datos de producción expuestas en repositorio público | **Bloqueante** |
| H-02 | Tres endpoints de migración de volumen sin autenticación (exportar/importar archivos del servidor) | **Bloqueante** |
| H-03 | JWT Secret con valor por defecto público en código fuente | **Bloqueante** |
| H-04 | Modo DEBUG de Flask activado por defecto en producción | **Bloqueante** |
| H-05 | Ausencia de control de autorización por rol en el backend (RBAC inexistente en API) | **Bloqueante** |
| H-06 | Endpoints de datos sensibles accesibles sin autenticación (documentos, geomapas, observaciones, reportes ciudadanos) | **Alta** |
| H-07 | Inyección de columnas SQL vía mass assignment en `update_proyecto` y `create_proyecto` | **Alta** |
| H-08 | Enumeración de usuarios activos mediante mensajes de error diferenciados en `/auth/login` | **Alta** |
| H-09 | Dirección IP privada del servidor hardcodeada en más de 15 archivos del frontend | **Alta** |
| H-10 | Datos personales de funcionarios municipales (nombres y correos electrónicos) expuestos en repositorio público | **Alta** |
| H-11 | Ausencia de Subresource Integrity (SRI) en recursos de CDN externos | **Alta** |
| H-12 | Endpoint `/health` expone información técnica de infraestructura sin autenticación | **Media** |
| H-13 | Endpoint `GET /proyectos/<pid>/documentos` con decorador `@session_required` deliberadamente comentado | **Media** |
| H-14 | Registro de información de autenticación sensible en logs de producción (Login DEBUG) | **Media** |
| H-15 | Logout no invalida el token JWT (no-op en `remove_session`) | **Media** |
| H-16 | Concatenación directa de nombre de tabla en funciones `crud_simple` y `generic_delete` | **Media** |
| H-17 | Archivos de debug y scripts de prueba presentes en el repositorio de producción | **Media** |
| H-18 | Archivos deprecados y código muerto accesibles públicamente | **Media** |
| H-19 | Token JWT almacenado en `localStorage` (expuesto a ataques XSS) | **Media** |
| H-20 | Divergencia entre documentación comercial y controles de seguridad reales | **Media** |
| H-21 | Módulo móvil y módulos de Seguridad/Transparencia fuera del alcance contractual declarado | **Baja** |
| H-22 | Vistas de administración sin responsividad móvil adecuada | **Baja** |
| H-23 | Dependencias de Python sin hashing de integridad verificable | **Baja** |
| H-24 | Tabla de auditoría sin ORDER BY (consulta `GET /auditoria`) | **Baja** |

---

## 2. OBJETIVO Y METODOLOGÍA

### 2.1 Alcance

La auditoría comprende el análisis estático del código fuente completo del repositorio `ALGARROBO_BASE2`, incluyendo:

- **Backend:** `backend/app21.py` (Flask/Python), `backend/correo.py`, `backend/debug_users.py`
- **Frontend:** Directorio `frontend/` completo (HTML/JS vanilla), directorio `movil/`
- **Base de datos:** Scripts SQL en directorio `database/`
- **Infraestructura:** `Dockerfile`, `ngnix.config`, `.gitignore`, archivos de configuración

### 2.2 Herramientas y Técnicas

- **Revisión manual del código fuente** (método principal)
- **Análisis estático automatizado:** `Bandit` (SAST para Python), `grep` con patrones de vulnerabilidades OWASP
- **Análisis de flujo de datos:** Trazado manual de rutas de autenticación y autorización desde el decorador `@session_required` hasta cada endpoint
- **Revisión de historial Git** para detectar credenciales comprometidas

### 2.3 Limitaciones

Esta auditoría es de naturaleza **estática**; no constituye un pentesting dinámico. Las vulnerabilidades identificadas se basan en lectura del código fuente. No se realizaron pruebas contra instancias activas ni se comprometió ningún sistema.

---

## 3. SEGURIDAD Y CONTROL DE ACCESO

### H-01 — Credenciales de Base de Datos de Producción en Repositorio Público
**Prioridad: Bloqueante**

- **Observación:** El archivo `backend/debug_users.py` contiene en texto claro la cadena de conexión completa a la base de datos PostgreSQL alojada en Neon.tech, incluyendo usuario, contraseña, host y nombre de base de datos: `postgresql://neondb_owner:npg_xHS7sA1FDPqI@ep-hidden-grass-a4sa46kc-pooler.us-east-1.aws.neon.tech/neondb`. Este archivo está incluido en el repositorio público de GitHub.

- **Impacto:** Cualquier persona con acceso a internet puede conectarse directamente a la base de datos de producción de la Municipalidad de Algarrobo, leer la totalidad de los proyectos, datos de funcionarios, documentos, auditorías y trazabilidad de acciones, modificar o eliminar registros de proyectos, y extraer la tabla `users` completa con correos electrónicos y hashes de contraseñas. Dado que el repositorio es público, esta credencial ya puede haber sido indexada por crawlers automáticos de secretos expuestos (como `truffleHog` o `GitGuardian`).

- **Recomendación:** Con carácter inmediato: (1) rotar la credencial de la base de datos en el panel de Neon.tech; (2) eliminar el archivo `debug_users.py` del repositorio y su historial mediante `git filter-repo`; (3) revisar los logs de acceso de Neon.tech para detectar conexiones anómalas. A largo plazo, todos los secretos deben gestionarse exclusivamente mediante variables de entorno (`.env`) nunca versionadas.

---

### H-02 — Endpoints de Migración de Volumen Sin Autenticación
**Prioridad: Bloqueante**

- **Observación:** El archivo `backend/app21.py` define tres rutas en el prefijo `/api/volume/` que carecen del decorador `@session_required`: `GET /api/volume/gui` (interfaz HTML administrativa), `GET /api/volume/export` (genera y descarga un ZIP con todos los documentos, reportes de auditoría y fotos del servidor) y `POST /api/volume/import` (recibe un archivo ZIP y lo extrae directamente en el sistema de archivos del servidor). Ninguna de estas rutas verifica identidad ni rol del solicitante.

- **Impacto:** Cualquier usuario anónimo puede, sin necesitar credenciales: descargar en un solo archivo ZIP toda la documentación técnica, legal y administrativa de todos los proyectos municipales (`GET /api/volume/export`), y subir un ZIP malicioso que sobreescriba archivos del servidor, incluyendo potencialmente código Python ejecutable dentro del directorio `backend/` si el proceso tiene permisos de escritura (`POST /api/volume/import`). Este segundo caso configura una vulnerabilidad de Remote Code Execution (RCE) — ejecución remota de código.

- **Recomendación:** Agregar inmediatamente el decorador `@session_required` a las tres rutas. Adicionalmente, la importación de ZIP debe validar que los nombres de archivo dentro del ZIP no contengan rutas de directorio traversal (`../`) usando `zipfile.ZipFile.namelist()`. Restringir estas operaciones a usuarios con `nivel_acceso >= 10` mediante verificación explícita en el backend.

---

### H-03 — JWT Secret con Valor por Defecto Público en Código Fuente
**Prioridad: Bloqueante**

- **Observación:** En `backend/app21.py`, línea 22: `JWT_SECRET = os.getenv("JWT_SECRET_KEY", "fallback-secret-for-dev-123456")`. Si la variable de entorno `JWT_SECRET_KEY` no está configurada en el servidor de producción, el sistema firma todos los tokens JWT con la cadena `"fallback-secret-for-dev-123456"`, que es públicamente visible en el repositorio.

- **Impacto:** Conociendo el secreto (que es público en GitHub), cualquier persona puede forjar tokens JWT válidos para cualquier `user_id`, incluyendo el del administrador del sistema. Esto equivale a tener la llave maestra de todas las sesiones de la plataforma, permitiendo autenticarse como cualquier usuario sin necesitar credenciales.

- **Recomendación:** Generar un JWT secret aleatorio de al menos 32 bytes (`secrets.token_hex(32)`) y almacenarlo exclusivamente como variable de entorno en producción. Agregar una validación al inicio de la aplicación que falle con error si `JWT_SECRET_KEY` no está definida, impidiendo el arranque con el valor de fallback.

---

### H-04 — Modo DEBUG de Flask Activado por Defecto en Producción
**Prioridad: Bloqueante**

- **Observación:** En `backend/app21.py`, línea 49: `DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("1", "true", "yes")`. El valor por defecto es `"True"`, lo que significa que si la variable `FLASK_DEBUG` no está definida explícitamente como `false` en el entorno de producción, Flask arranca en modo depuración.

- **Impacto:** El modo DEBUG de Flask habilita el debugger interactivo de Werkzeug, que permite ejecutar código Python arbitrario en el servidor desde el navegador al producirse una excepción. Adicionalmente, expone trazas de error completas con rutas de archivo del servidor, nombres de variables internas y fragmentos de código fuente a cualquier usuario que provoque un error.

- **Recomendación:** Cambiar el valor por defecto a `"False"`: `DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("1", "true", "yes")`. Verificar que la variable esté explícitamente seteada a `0` o `false` en todos los entornos de producción y staging.

---

### H-05 — Ausencia de Control de Autorización por Rol en el Backend (RBAC Inexistente)
**Prioridad: Bloqueante**

- **Observación:** El decorador `@session_required` en `backend/app21.py` únicamente verifica que el token JWT sea válido y extrae el `user_id`. No verifica el `nivel_acceso` del usuario ni sus roles asignados en la tabla `user_roles`. Todos los endpoints protegidos (creación/eliminación de usuarios, reseteo de contraseñas, gestión de roles, creación de licitaciones, etc.) son accesibles por cualquier usuario autenticado, independientemente de su nivel. La única excepción es `crear_funcionario` (`/api/admin/crear-funcionario`), que sí verifica `nivel_acceso >= 10`.

- **Impacto:** Un usuario con el rol "Vecino" (nivel_acceso=0), creado mediante el endpoint público `/api/mobile/auth/register`, puede: hacer `DELETE /users/<id>` para eliminar cuentas de otros usuarios; hacer `PUT /users/<id>/reset-password` para cambiar la contraseña de cualquier funcionario, incluyendo administradores; acceder a toda la información de proyectos, documentos y auditorías; y gestionar licitaciones. Concretamente, un vecino registrado a través de la app móvil tiene los mismos privilegios efectivos que el administrador del sistema.

- **Recomendación:** Implementar un segundo decorador `@role_required(nivel_minimo)` que verifique el nivel de acceso del usuario antes de cada operación sensible. Definir una matriz de control de acceso explícita: operaciones de usuarios y roles (nivel 10), creación/eliminación de proyectos (nivel 3), lectura de proyectos (nivel 1). Aplicar el principio de mínimo privilegio (OWASP A01:2021 — Broken Access Control).

---

### H-06 — Endpoints de Datos Sensibles Accesibles Sin Autenticación
**Prioridad: Alta**

- **Observación:** Los siguientes endpoints carecen del decorador `@session_required` y son accesibles sin ninguna credencial:
  - `GET /proyectos/<pid>/documentos` — lista los documentos de un proyecto (decorador comentado: `#@session_required`)
  - `GET /proyectos/<pid>/geomapas` — lista los geomapas GeoJSON de un proyecto
  - `GET /proyectos/<pid>/observaciones` — lista las observaciones técnicas de un proyecto
  - `GET /api/mobile/reportes/todos` — retorna la totalidad de reportes ciudadanos con nombres, emails del reportante, coordenadas GPS y descripciones
  - `GET /api/licitaciones/docs/<filename>` y `GET /api/licitaciones/lib/<filename>` — sirven archivos de licitación directamente

- **Impacto:** Cualquier persona con acceso a la URL del servidor puede obtener documentos técnicos y legales de proyectos municipales, datos personales de ciudadanos que realizaron reportes (nombre, email, ubicación GPS), y archivos de licitaciones sin estar autenticada. Esto constituye una potencial infracción a la Ley 19.628 de Protección de la Vida Privada.

- **Recomendación:** Agregar `@session_required` a todos los endpoints listados. Restaurar el decorador en `listar_documentos_proyecto` (actualmente comentado en la línea 2407). Para los endpoints de servicio de archivos, considerar adicionalmente la generación de URLs firmadas con tiempo de expiración.

---

### H-07 — Inyección de Columnas SQL Vía Mass Assignment
**Prioridad: Alta**

- **Observación:** La función `update_proyecto` (línea ~1830) construye la cláusula `SET` de una sentencia SQL usando directamente las claves del JSON recibido del cliente: `for k, v in clean_data.items(): fields.append(f"{k} = %s")`. Aunque hay una lista `forbidden` que excluye algunos campos, no existe una lista blanca (allowlist) de columnas permitidas. La misma vulnerabilidad existe en `create_proyecto` (línea ~1337), donde `cols = ", ".join(clean_data.keys())` genera las columnas del INSERT directamente desde el body del request.

- **Impacto:** Un usuario autenticado puede enviar en el body de un `PUT /proyectos/<id>` claves arbitrarias, incluyendo columnas sensibles como `user_id` (cambiar la propiedad del proyecto a otro usuario), `activo` (reactivar proyectos eliminados), o columnas que no deberían ser modificables por el usuario. Si el servidor usa PostgreSQL con extensiones como `lo_read`, un nombre de columna malformado podría provocar errores que filtren información de la base de datos. Esto corresponde a OWASP A03:2021 — Injection (variante Mass Assignment).

- **Recomendación:** Reemplazar el enfoque de lista negra (`forbidden`) por una lista blanca explícita de columnas editables (`ALLOWED_PROYECTO_FIELDS = {"nombre", "descripcion", "monto", ...}`). Iterar solo sobre ese conjunto: `clean_data = {k: v for k, v in data.items() if k in ALLOWED_PROYECTO_FIELDS}`.

---

### H-08 — Enumeración de Usuarios Mediante Mensajes de Error Diferenciados
**Prioridad: Alta**

- **Observación:** El endpoint `POST /auth/login` retorna mensajes de error distintos según el estado del usuario: `{"message": "Usuario no encontrado"}` (HTTP 404) cuando el email no existe; `{"message": "Usuario inactivo"}` (HTTP 403) cuando existe pero está deshabilitado; y `{"message": "Contraseña incorrecta"}` (HTTP 401) cuando la contraseña es incorrecta.

- **Impacto:** Un atacante puede usar estos mensajes para enumerar de forma sistemática qué correos electrónicos tienen cuenta activa en el sistema, distinguir cuentas activas de inactivas, y focalizar ataques de fuerza bruta solo en cuentas existentes y activas. Esto corresponde a OWASP A07:2021 — Identification and Authentication Failures.

- **Recomendación:** Unificar todos los casos de fallo en un único mensaje genérico: `{"message": "Credenciales inválidas"}` con código HTTP 401, independientemente de si el usuario no existe, está inactivo o la contraseña es incorrecta.

---

## 4. ANÁLISIS ESTÁTICO DE CÓDIGO (SAST)

### H-09 — Dirección IP de Servidor Hardcodeada en Más de 15 Archivos
**Prioridad: Alta**

- **Observación:** La dirección IP `186.67.61.251:8000` (presumiblemente el servidor de desarrollo o producción del proveedor) aparece hardcodeada en al menos 16 archivos del frontend, incluyendo `frontend/script/api.js` (línea 7), `movil/scripts/api.js` (línea 6), `frontend/documento.html` (línea 37), `frontend/vizualizar.html` (línea 22), y múltiples vistas en `frontend/division/`. Adicionalmente, en `frontend/administracion/index2.html` hay un enlace directo a `http://186.67.61.251:8000/api/volume/gui` usando HTTP en lugar de HTTPS.

- **Impacto:** Expone la arquitectura de red interna del proveedor y hace que el sistema sea completamente no mantenible: cualquier cambio de servidor requiere editar manualmente decenas de archivos. El enlace HTTP en `index2.html` expone la interfaz de migración (que ya es pública sin autenticación) sobre un canal no cifrado, permitiendo interceptación en redes intermedias.

- **Recomendación:** Centralizar la URL base en una única variable de configuración (`window.API_BASE_URL` ya existe como mecanismo de override, pero no está siendo inyectada). Implementar un archivo `config.js` con la URL base como constante, o inyectarla a través del servidor. Remover todos los hardcoded IPs. El enlace HTTP debe cambiarse a HTTPS.

---

### H-10 — Datos Personales de Funcionarios Expuestos en Repositorio Público
**Prioridad: Alta**

- **Observación:** El archivo `backend/config_correo.json` contiene un mapeo de apellidos a correos electrónicos institucionales de 15 funcionarios municipales (ej. `"Araya": "saraya@munialgarrobo.cl"`). Este archivo está versionado en el repositorio público de GitHub.

- **Impacto:** Los datos personales de funcionarios municipales son accesibles públicamente, en potencial infracción a la Ley 19.628. Estos datos pueden ser usados para ataques de spear phishing dirigidos a funcionarios específicos, o para intentar acceder a sus cuentas en el sistema.

- **Recomendación:** Mover `config_correo.json` a una variable de entorno o a una tabla de la base de datos. Eliminarlo del historial del repositorio con `git filter-repo`. Si se mantiene como archivo de configuración, excluirlo del versionamiento mediante `.gitignore`.

---

### H-11 — Ausencia de Subresource Integrity (SRI) en Recursos de CDN
**Prioridad: Alta**

- **Observación:** El frontend carga múltiples librerías desde CDNs externos sin atributo `integrity`: Tailwind CSS desde `cdn.tailwindcss.com`, Font Awesome desde `cdnjs.cloudflare.com`, y Leaflet desde `unpkg.com`. Ninguno de estos `<script>` o `<link>` incluye el atributo `integrity="sha384-..."`.

- **Impacto:** Si cualquiera de estos CDNs fuera comprometido (ataque de supply chain), el código malicioso inyectado en la librería se ejecutaría con todos los privilegios del frontend, pudiendo robar tokens JWT del `localStorage` de los usuarios o capturar contraseñas. La falta de SRI elimina la única defensa del navegador contra este vector de ataque. Esto corresponde a OWASP A06:2021 — Vulnerable and Outdated Components.

- **Recomendación:** Generar los hashes SRI para cada recurso externo usando `openssl dgst -sha384 -binary archivo.js | openssl base64 -A` e incluirlos como atributo `integrity` en cada tag. Evaluar alojar las librerías localmente en el repositorio para eliminar la dependencia de CDNs externos.

---

### H-16 — Concatenación Directa de Nombre de Tabla en Funciones Auxiliares
**Prioridad: Media**

- **Observación:** Las funciones `crud_simple` (línea ~1919) y `generic_delete` (línea ~1986) construyen queries SQL concatenando directamente el nombre de la tabla como string: `cur.execute("SELECT * FROM " + str(tabla))` y `cur.execute("UPDATE " + str(table_name) + " SET activo = FALSE WHERE id = %s", (id,))`. Actualmente estas funciones solo son llamadas con strings literales desde el código del proveedor, pero el patrón es inherentemente inseguro.

- **Impacto:** Si en futuras modificaciones un nombre de tabla llegara a ser controlado por el usuario, esto abriría un vector de inyección SQL directa. La práctica de concatenar nombres de objetos SQL viola el principio de parametrización de queries.

- **Recomendación:** Usar un enfoque de lista blanca para los nombres de tabla permitidos: `ALLOWED_TABLES = {"areas", "financiamientos", ...}`. Validar que `table_name in ALLOWED_TABLES` antes de ejecutar cualquier query. Los identificadores de objetos SQL (tablas, columnas) no pueden ser parametrizados con `%s` en psycopg2; la alternativa segura es `psycopg2.extensions.AsIs` con validación estricta de whitelist.

---

## 5. INFRAESTRUCTURA Y GOBERNANZA DE DATOS

### H-12 — Endpoint `/health` Expone Información Técnica Sin Autenticación
**Prioridad: Media**

- **Observación:** El endpoint `GET /health` (sin `@session_required`) retorna información técnica detallada incluyendo: estado del pool de conexiones (min/max conexiones activas), estado de la base de datos, fragmento del connection string (hostname de la base de datos), versión del sistema y que está "optimizado para Railway". Todo esto es accesible sin ninguna autenticación.

- **Impacto:** Esta información ayuda a un atacante a comprender la arquitectura del sistema, identificar el proveedor de base de datos (Railway/Neon), y confirmar la topología de red. Constituye una filtración de información (OWASP A05:2021 — Security Misconfiguration).

- **Recomendación:** Restringir `/health` a solicitudes autenticadas, o bien reducir la información retornada a un simple `{"status": "ok"}` para el uso de health checks externos, y proveer la información detallada solo a administradores autenticados.

---

### H-13 — Decorador `@session_required` Deliberadamente Comentado
**Prioridad: Media**

- **Observación:** En `backend/app21.py`, líneas 2407-2409, el decorador de autenticación y la firma de función con `current_user_id` han sido explícitamente comentados para el endpoint `GET /proyectos/<pid>/documentos`, resultando en una función pública `listar_documentos_proyecto(pid)`:

```python
#@session_required
#def listar_documentos_proyecto(current_user_id, pid):
def listar_documentos_proyecto(pid):
```

- **Impacto:** La remoción deliberada del control de acceso sugiere que fue una decisión intencional del proveedor, posiblemente para simplificar el desarrollo. Cualquier persona puede enumerar los documentos de cualquier proyecto conociendo su ID numérico.

- **Recomendación:** Restaurar el decorador y la firma correcta de la función. Documentar cualquier decisión de apertura de endpoints mediante un RFC interno aprobado por el Departamento de Informática.

---

## 6. HIGIENE DEL REPOSITORIO Y DEUDA TÉCNICA

### H-17 — Archivos de Debug y Scripts de Prueba en Repositorio de Producción
**Prioridad: Media**

- **Observación:** El directorio `backend/` contiene los siguientes archivos de desarrollo que no deben estar presentes en un entorno de producción: `debug_users.py` (conecta a BD y vuelca todos los usuarios), `test_bcrypt.py` (pruebas de hashing), `test_db.py` (pruebas de conexión a BD). El directorio `frontend/division/secplan/admin_general/` contiene `test.js` y `test_script.js`.

- **Impacto:** Además de contener credenciales (H-01), estos scripts podrían ser ejecutados accidentalmente en producción. La presencia de archivos de test en código de entrega indica un proceso de control de calidad insuficiente por parte del proveedor.

- **Recomendación:** Eliminar todos los archivos de debug y test del repositorio. Definir un proceso de entrega que incluya una revisión de archivos antes del commit final: ningún archivo con prefijo `debug_`, `test_` o `check_` debe estar en el entregable final.

---

### H-18 — Archivos Deprecados y Código Muerto Accesibles por URL
**Prioridad: Media**

- **Observación:** Existen dos archivos con nomenclatura explícita de deprecación accesibles por URL directa: `frontend/division/secplan/admin_proyectos/chat_deprecated.html` y `frontend/division/seguridad/admin_proyectos/chat_deprecated.html`. Adicionalmente, el módulo de chat tiene endpoints en el backend que podrían no estar mantenidos. El comentario `# Mantener endpoint antiguo por compatibilidad` en `verificar_reporte` (línea ~3905) indica deuda técnica acumulada.

- **Impacto:** Los archivos deprecados pueden contener vulnerabilidades conocidas que no reciben correcciones, y su existencia como URLs accesibles amplía innecesariamente la superficie de ataque. Constituyen "Shadow UIs" (interfaces duplicadas) que pueden ser descubiertas por atacantes.

- **Recomendación:** Eliminar todos los archivos con sufijo `_deprecated` del repositorio. Documentar y eliminar el endpoint `verificar_reporte` si es solo un alias del endpoint `actualizar_reporte`.

---

### H-19 — Token JWT Almacenado en `localStorage`
**Prioridad: Media**

- **Observación:** En `frontend/script/api.js` (línea 8) y `movil/scripts/api.js`, el token JWT se almacena y lee desde `localStorage.getItem('authToken')` y `localStorage.getItem('token')`. El `localStorage` es accesible desde cualquier script JavaScript que corra en la misma página (incluyendo scripts de terceros inyectados).

- **Impacto:** Si se introdujera un vector de XSS (Cross-Site Scripting) en el frontend, el atacante podría robar el token JWT con `document.cookie` no siendo necesario, pero sí con `localStorage.getItem('authToken')`, y usarlo para suplantar la sesión del usuario en el backend.

- **Recomendación:** Almacenar los tokens JWT en cookies con atributos `HttpOnly` (inaccesibles desde JavaScript) y `Secure` (solo HTTPS). Esto requiere cambios coordinados en el backend para emitir la cookie en el login y leerla en el middleware de autenticación.

---

### H-15 — Logout No Invalida el Token JWT
**Prioridad: Media**

- **Observación:** La función `remove_session` en `backend/app21.py` es un no-op explícito con comentario `"""JWT Stateless: No-op."""`. Al hacer logout, el token no es invalidado en ningún almacén del servidor.

- **Impacto:** Si un token es interceptado o robado antes del logout, seguirá siendo válido hasta su expiración natural (24 horas configuradas en `SESSION_EXPIRY_HOURS`). Un funcionario que cierra sesión en un equipo compartido o robado no puede invalidar efectivamente su sesión.

- **Recomendación:** Implementar una blocklist de tokens invalidados en base de datos o Redis. Al hacer logout, registrar el `jti` (JWT ID) del token en esta lista. El decorador `validate_session` debe verificar que el token no esté en la blocklist antes de autorizarlo.

---

### H-14 — Registro de Información de Autenticación Sensible en Logs
**Prioridad: Media**

- **Observación:** En `backend/app21.py`, línea 3851-3852, dentro de `login_mobile`: `logger.info(f"LOGIN DEBUG: User {u['email']} - Nivel Acceso: {u.get('nivel_acceso')}")`. Esta línea de debug registra el email del usuario y su nivel de acceso en el log de la aplicación cada vez que se autentica desde la app móvil.

- **Impacto:** Los logs de aplicación típicamente tienen menor protección que la base de datos. Registrar emails de usuarios en logs en texto plano puede violar normativas de privacidad y facilita la exposición de datos en caso de acceso no autorizado a los archivos de log.

- **Recomendación:** Eliminar o reemplazar esta línea por una versión que no incluya el email completo: `logger.info(f"LOGIN mobile: user_id={u['user_id']}")`. Revisar todos los logs para asegurar que no contengan contraseñas, tokens ni datos personales completos.

---

## 7. DOCUMENTACIÓN TÉCNICA

### H-20 — Divergencia Entre Documentación Comercial y Controles de Seguridad Reales
**Prioridad: Media**

- **Observación:** El archivo `propuesta.md` (documento comercial incluido en el repositorio) describe controles de seguridad que no se corresponden con la implementación real. La propuesta declara: "Sesiones controladas y monitoreadas activamente, con capacidad de revocación inmediata" — en la realidad, `remove_session` es un no-op y no existe revocación. Declara "sofisticado modelo de Control de Acceso Basado en Roles (RBAC)" — en la realidad, todos los usuarios autenticados tienen acceso a todos los endpoints.

- **Impacto:** La institución tomó decisiones de contratación basándose en capacidades de seguridad declaradas que no existen en el código. Esto puede tener consecuencias contractuales y legales, además de generar una falsa sensación de seguridad en los administradores del sistema.

- **Recomendación:** Solicitar al proveedor una reconciliación formal entre las funcionalidades de seguridad declaradas en la propuesta y las implementadas en el código. Las diferencias deben ser corregidas antes de la recepción o documentadas formalmente como exclusiones del alcance.

---

## 8. USABILIDAD MÓVIL

### H-22 — Vistas de Administración Sin Responsividad Móvil
**Prioridad: Baja**

- **Observación:** Las vistas del panel de administración (`frontend/administracion/usuario.html`, `sistema.html`, `proyectos.html`) utilizan tablas HTML de múltiples columnas sin breakpoints responsivos ni clases Tailwind de adaptación móvil (como `sm:`, `md:`). Las vistas principales de SECPLAC (`frontend/division/secplan/admin_general/dashboard.html`) tampoco implementan layouts adaptados a pantallas pequeñas más allá del meta viewport básico.

- **Impacto:** El sistema no es operativo en dispositivos móviles para las funciones de administración y gestión de proyectos, lo que limita su uso en contextos de terreno y visitas a obra.

- **Recomendación:** Aplicar diseño responsivo usando las utilidades de Tailwind CSS ya incluidas en el proyecto (`sm:hidden`, `overflow-x-auto` en tablas, layouts de columna única en pantallas pequeñas). Considerar el uso de componentes de Tailwind UI adaptados para móvil.

---

## 9. ALCANCE DEL PROYECTO

### H-21 — Módulos Fuera del Alcance Contractual Declarado Sin Notificación
**Prioridad: Baja**

- **Observación:** El repositorio contiene módulos y divisiones cuya presencia no fue declarada en la propuesta comercial orientada a SECPLAC: (1) Directorio `frontend/division/seguridad/` con un módulo completo de gestión de delitos (CEAD) con 26 vistas (`vista0.html` a `vista25.html`), integración con IA y gestión de datos criminales; (2) Directorio `frontend/division/transparencia/` con un módulo de remuneraciones y datos de OIRS; (3) Directorio `movil/` con una aplicación móvil completa de reportes ciudadanos; (4) Una API de administración de funcionarios (`/api/admin/crear-funcionario`) no documentada.

- **Impacto:** La institución recibe código no contratado ni auditado, cuya calidad, seguridad y mantenimiento no puede ser garantizada. Estos módulos amplían la superficie de ataque del sistema sin respaldo contractual. Adicionalmente, el módulo de seguridad maneja datos criminales sensibles cuyo procesamiento podría requerir medidas de seguridad adicionales.

- **Recomendación:** Solicitar al proveedor la declaración formal de todos los módulos incluidos y su correspondencia con el contrato. Los módulos fuera de alcance deben ser separados en ramas distintas del repositorio o eliminados del entregable, y su recepción debe ser tratada como una adenda contractual independiente con su propia evaluación de seguridad.

---

## 10. CONCLUSIÓN GENERAL

### Veredicto Técnico

**El sistema NO se encuentra en condiciones de ser recepcionado contractualmente ni de ser puesto en operación en un entorno de producción.**

Los hallazgos H-01 a H-05 constituyen vulnerabilidades de nivel **Bloqueante** que representan riesgos inmediatos para la seguridad de la información municipal: credenciales de producción ya comprometidas públicamente en GitHub, endpoints administrativos anónimos que permiten extracción masiva y sobreescritura de datos del servidor, y una arquitectura de autorización que no implementa ningún control de acceso por rol en el backend a pesar de declararlo en la documentación comercial.

La gravedad de estos hallazgos es especialmente preocupante considerando que: (1) las credenciales de base de datos (H-01) ya están públicas y deben rotarse con carácter de urgencia independientemente de la decisión de recepción; (2) los endpoints de migración (H-02) configuran la vulnerabilidad más crítica, pues no requieren ningún tipo de autenticación para descargar toda la documentación municipal o subir código malicioso.

### Condiciones para Recepción

La recepción formal del sistema debe condicionarse a la corrección verificada de los siguientes hallazgos como mínimo:

1. **H-01:** Rotación de credenciales y eliminación del historial Git (acción inmediata, independiente de la recepción)
2. **H-02:** Agregar autenticación y control de rol a los tres endpoints de volumen
3. **H-03:** Eliminar el valor de fallback del JWT_SECRET del código
4. **H-04:** Cambiar el default de FLASK_DEBUG a `"False"`
5. **H-05:** Implementar verificación de nivel de acceso en endpoints administrativos
6. **H-06:** Restaurar `@session_required` en todos los endpoints listados
7. **H-10:** Eliminar datos de funcionarios del repositorio

Los hallazgos de prioridad Alta (H-07 a H-12) deben ser corregidos dentro de un plazo máximo de 30 días hábiles posterior a la recepción condicional. Los de prioridad Media y Baja pueden incluirse en el plan de mantenimiento correctivo regular.

Se recomienda que el Departamento de Informática realice una verificación técnica independiente de cada corrección antes de autorizar la puesta en producción del sistema.

---

*Fin del Informe Técnico de Auditoría*  
*Departamento de Informática — Municipalidad de Algarrobo*  
*Marzo 2026*
