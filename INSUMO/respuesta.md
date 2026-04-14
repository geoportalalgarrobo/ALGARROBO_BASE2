# Evaluación de Auditoría de Ciberseguridad - Geoportal Municipal

Este documento detalla el estado actual de cada hallazgo reportado en `INSUMO/revision.md`, mapeando las intervenciones técnicas realizadas en el código fuente y determinando si el punto ha sido resuelto, está parcialmente abordado o sigue pendiente.

---

## 3. Hallazgos Críticos de Seguridad y Control de Acceso

### 3.1 Control de Acceso
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `frontend/script/router.js`, `frontend/script/layout.js`, `backend/app21.py`
- **Detalle:** Se implementó verificación de roles en dos capas:
  - **Frontend:** `router.js` contiene la función `checkLoginStatus()` que valida la presencia de un token y verifica que el `role_id` del usuario pertenezca al conjunto de roles autorizados (`[10, 11]`). Cualquier usuario sin rol válido es redirigido inmediatamente al login.
  - **Backend:** Todos los endpoints sensibles están protegidos por el decorador `@session_required`, que valida la firma y expiración del JWT en cada request.

### 3.2 Principio de Menor Privilegio
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `frontend/script/router.js`
- **Detalle:** El sistema restringe el acceso operativo a exactamente 2 roles definidos:`admin_general` (id 10) y `admin_proyectos` (id 11). El diccionario `diccionarioRutas` en `router.js` mapea explícitamente qué rutas puede visitar cada rol, sin posibilidad de escalada. Se eliminaron los fallbacks que otorgaban privilegios por defecto.

### 3.3 Configuración Permisiva de CORS
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py` (líneas 57–70)
- **Detalle:** Se eliminó el comodín `*`. La configuración ahora lee la variable de entorno `ALLOWED_ORIGINS` (lista separada por comas) para construir una lista blanca dinámica. Si la variable no está definida, el fallback aplica únicamente orígenes de desarrollo local (`localhost:8000`, `127.0.0.1:8000`, `localhost:3000`). Las reglas de CORS se aplican solo a rutas `/api/*` y `/auth/*`.

### 3.4 Rutas API sin uso (Shadow APIs)
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py`
- **Detalle:** Se eliminó el endpoint duplicado `/auth/login2`. Se auditaron las rutas del backend y no se detectan endpoints dobles activos.

### 3.5 Asignación Insegura por Defecto
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `frontend/script/router.js`, `frontend/script/layout.js`
- **Detalle:** Se eliminó el patrón donde el sistema asignaba `admin_general` por defecto cuando los datos de sesión estaban incompletos. Ahora, cualquier inconsistencia en los datos de rol resulta en un cierre de sesión automático y redirección al login.

### 3.6 Dependencias de Terceros
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/requirements.txt`
- **Detalle:** Se implementó versionado estricto de todas las dependencias del backend (Flask 3.0.0, psycopg2-binary 2.9.9, PyJWT 2.8.0, bcrypt 4.1.2, etc.). Esto previene la instalación de versiones con vulnerabilidades no evaluadas por el equipo.

---

## 4. Resultados de Análisis Estático (SAST)

### 4.1 Inyección SQL
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py`
- **Detalle:** Todas las consultas a base de datos utilizan parametrización nativa de `psycopg2` (mediante el patrón `cursor.execute(sql, (param1, param2))`), eliminando la construcción dinámica de SQL con datos del cliente.

### 4.2 XSS (Cross-Site Scripting)
- **Estado:** ✅ **RESUELTO**
- **Detalle:** Se reemplazó el uso extendido de `.innerHTML` mediante un script automatizado de Node.js que procesó 125 archivos HTML, integrando sanitización a través de `DOMPurify`. La librería fue inyectada en los encabezados de cada vista afectada.

### 4.3 Integridad de Dependencias (SRI)
- **Estado:** ✅ **RESUELTO**
- **Detalle:** Se implementó Subresource Integrity (SRI) en todas las etiquetas `<script>` y `<link>` que hacen referencia a recursos de CDNs externos, junto con el atributo `crossorigin="anonymous"`, evitando que recursos comprometidos en el CDN afecten la aplicación.

---

## 5. Infraestructura y Gobernanza de Datos

### 5.1 Connection Pool
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py` (función `get_db_connection`, líneas 155–181)
- **Detalle:** Se configuró un `ThreadedConnectionPool` con `maxconn=20` y una validación activa de conexiones (`SELECT 1`) antes de reutilizarlas. Se habilitaron keepalives TCP para evitar que conexiones inactivas sean descartadas por el broker de NeonDB/Railway.

### 5.2 Seguridad en IA (Chatbot)
- **Estado:** ⚠️ **PARCIALMENTE RESUELTO**
- **Archivos:** `frontend/script/router.js` (función `getKey`)
- **Detalle:** La API Key del proveedor de IA (ZhipuAI) fue ofuscada mediante XOR con la función `getKey()`. Si bien esto eleva la barrera de acceso casual, la llave sigue siendo técnicamente recuperable mediante las DevTools del navegador.
- **Urgencia:** **MEDIA** — Se recomienda mover el consumo del modelo de IA al backend (`app21.py`) para que la API Key nunca salga del servidor.

### 5.3 Filtración de Credenciales
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py`, `backend/.env`
- **Detalle:** Los secretos críticos (cadena de conexión a la BD, JWT Secret, orígenes CORS) se gestionan exclusivamente a través de variables de entorno cargadas con `load_dotenv()`. El archivo `.env` está incluido en `.gitignore`.

### 5.4 Credenciales por Defecto
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py` (función `create_user`)
- **Detalle:** Las contraseñas son hasheadas con `bcrypt` en el momento de la creación del usuario. No se detectan contraseñas débiles predefinidas en el código.

### 5.5 Transaccionalidad
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py`
- **Detalle:** Se inyectaron bloques `try/except` con llamadas a `conn.rollback()` en todas las funciones críticas de base de datos, asegurando que las operaciones fallidas no dejen la base de datos en un estado inconsistente.

### 5.6 Manejo de Sesiones
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py` (funciones `create_session`, `validate_session`)
- **Detalle:** Se migró del modelo de sesiones en memoria RAM (volátil y no escalable) a un sistema **JWT stateless** usando `PyJWT`. Los tokens incluyen `exp` (expiración a 24h) e `iat` (fecha de emisión), garantizando persistencia y compatibilidad con despliegues multi-instancia.

---

## 6. Higiene del Repositorio y Deuda Técnica

### 6.1 Archivos Residuales
- **Estado:** ⚠️ **PARCIALMENTE RESUELTO**
- **Detalle:** Se eliminaron los scripts de prueba numerados (`test_script_0.js` a `test_script_9.js`) y el directorio `notebook/`. Sin embargo, se detectan archivos residuales adicionales en el repositorio: `frontend/division/secplan/admin_general/test.js`, `test_script.js`, y diversas interfaces duplicadas (ver 6.3).

### 6.2 Hardcoding de IP
- **Estado:** ⚠️ **PARCIALMENTE RESUELTO**
- **Archivos:** `frontend/script/api.js` (línea 7)
- **Detalle:** Se eliminaron las IPs de la configuración de CORS en el backend. Sin embargo, persiste una IP de fallback hardcodeada en el cliente: `BASE_URL: window.API_BASE_URL || "https://algarrobobase2-production-4ab9.up.railway.app"`.
- **Urgencia:** **BAJA** — La IP actúa como fallback de desarrollo. Se recomienda eliminarla y exigir que `window.API_BASE_URL` sea siempre inyectada por el entorno de despliegue.

### 6.3 Interfaces Duplicadas
- **Estado:** ⚠️ **PARCIALMENTE RESUELTO**
- **Archivos detectados:** `frontend/administracion/index2.html`, `frontend/geoportal/2.html`, `frontend/division/secplan/admin_general/mapa2.html`, `informe_dinamico2.html`, entre otros.
- **Detalle:** Se implementó un diccionario de rutas en `router.js` que limita el acceso según el rol, mitigando el riesgo. Sin embargo, los archivos de las interfaces antiguas aún existen en el repositorio.
- **Urgencia:** **MEDIA** — Se recomienda eliminar estos archivos para reducir la superficie de ataque.

### 6.4 Sobrescritura de Contraseñas Vacías
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py` (función `update_user`, líneas 709–763)
- **Detalle:** La función `update_user` solo actualiza el `password_hash` cuando el campo `password` es explícitamente enviado en el payload. Las contraseñas vacías no son procesadas ya que el campo `password` no estará en el conjunto `allowed` si no se envía.

### 6.5 Manejo de Errores
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `backend/app21.py` (función `handle_exception`, líneas 78–84)
- **Detalle:** Se implementó un manejador global de excepciones con `@app.errorhandler(Exception)`. El error real se registra en el log del servidor, pero al cliente solo se devuelve el mensaje genérico `"An internal error occurred"`.

### 6.6 Enrutamiento
- **Estado:** ✅ **RESUELTO**
- **Archivos:** `frontend/script/router.js`
- **Detalle:** Se implementó un diccionario de rutas completo y explícito por rol. La función `verificarRutaPermitida()` evalúa la ruta activa contra el mapa del rol autenticado, eliminando los bucles de redirección anteriores.

---

## 7. Documentación Técnica

- **Estado:** ✅ **RESUELTO**
- **Detalle:** Se alineó la implementación con la arquitectura declarada. JWT está completamente funcional (`create_session` / `validate_session` con `PyJWT`). El framework Flask está correctamente configurado con todas sus dependencias definidas. Los errores internos ya no son expuestos al cliente.

---

## 8. Usabilidad en Móviles

- **Estado:** 🔴 **PENDIENTE**
- **Archivos:** `frontend/division/secplan/admin_general/styles/admin-styles.css`
- **Detalle:** No se detectan reglas `@media queries` en los archivos de estilos principales, confirmando que el menú lateral y las tablas del sistema siguen sin adaptarse a pantallas pequeñas.
- **Urgencia:** **MEDIA** — Se recomienda agregar breakpoints responsivos para resoluciones menores a 768px como mínimo.

---

## 9. Alcance del Proyecto

- **Estado:** ⚠️ **PENDIENTE DE DECISIÓN**
- **Detalle:** Existen módulos fuera del alcance del encargo original: `movil/` (API móvil), `frontend/geoportal/`, páginas de vecinos, y otros. Estos módulos aumentan la superficie de ataque del sistema y representan deuda técnica activa.
- **Urgencia:** **ALTA** — Se recomienda definir con el cliente cuáles módulos son parte del alcance contractual y eliminar o desactivar los que no lo sean.

---

## Conclusión

| Sección | Resueltos | Parciales | Pendientes |
|---|---|---|---|
| 3. Control de Acceso | 5 | 0 | 0 |
| 4. SAST | 3 | 0 | 0 |
| 5. Infraestructura | 4 | 1 | 0 |
| 6. Higiene del Repo | 3 | 3 | 0 |
| 7. Documentación | 1 | 0 | 0 |
| 8. Móviles | 0 | 0 | 1 |
| 9. Alcance | 0 | 0 | 1 |
| **Total** | **16** | **4** | **2** |

Se han resuelto aproximadamente el **73% de los puntos** reportados. Los puntos parciales y pendientes de mayor urgencia son:

1. **API Key de IA expuesta en el cliente** → Mover el consumo al backend.
2. **IP hardcodeada en `api.js`** → Parametrizar mediante variable de entorno.
3. **Archivos de interfaces duplicadas** → Eliminar del repositorio.
4. **Responsividad móvil** → Implementar `@media queries`.
5. **Módulos fuera de alcance** → Definir con el cliente y eliminar los que no correspondan.
