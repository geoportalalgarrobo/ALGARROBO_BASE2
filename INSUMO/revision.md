# Informe de Auditoría Técnica de Seguridad

```
Proyecto:              Geoportal Municipal – Municipalidad de Algarrobo
Repositorio:           https://github.com/geoportalalgarrobo/ALGARROBO_BASE2
Lenguaje/Framework:    Python 3.11 / Flask 3.0 + Vanilla JS (Frontend estático)
Base de datos:         PostgreSQL (Railway Cloud)
Fecha de auditoría:    30 de marzo de 2026
Clasificación:         CONFIDENCIAL — USO INTERNO
Versión del informe:   1.0
```

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
   - 1.1 [Dashboard de Riesgo](#11-dashboard-de-riesgo)
   - 1.2 [Tabla Maestra de Hallazgos](#12-tabla-maestra-de-hallazgos)
2. [Objetivo y Metodología](#2-objetivo-y-metodología)
3. [Seguridad y Control de Acceso](#3-seguridad-y-control-de-acceso)
4. [Análisis Estático de Código (SAST)](#4-análisis-estático-de-código-sast)
5. [Infraestructura y Gobernanza de Datos](#5-infraestructura-y-gobernanza-de-datos)
6. [Higiene del Repositorio y Deuda Técnica](#6-higiene-del-repositorio-y-deuda-técnica)
7. [Documentación Técnica](#7-documentación-técnica)
8. [Usabilidad, Accesibilidad y Diseño Responsivo](#8-usabilidad-accesibilidad-y-diseño-responsivo)
9. [Alcance Contractual y Cumplimiento de Requerimientos](#9-alcance-contractual-y-cumplimiento-de-requerimientos)
10. [Cadena de Suministro de Software](#10-cadena-de-suministro-de-software)
11. [Resiliencia y Continuidad Operacional](#11-resiliencia-y-continuidad-operacional)
12. [Conclusión General y Veredicto Técnico](#12-conclusión-general-y-veredicto-técnico)

---

## 1. Resumen Ejecutivo

El sistema auditado es el **Geoportal Municipal de Algarrobo**, una plataforma web integral de gestión de proyectos, licitaciones, auditoría interna y reportes ciudadanos para la Ilustre Municipalidad de Algarrobo. Comprende un backend API REST en Python/Flask desplegado en Railway, un frontend estático HTML/JavaScript alojado en GitHub Pages, y una base de datos PostgreSQL en la nube.

La revisión estática del código fuente identificó **seis (6) hallazgos de severidad Bloqueante** que impiden categóricamente la recepción contractual o el pase a un entorno de producción institucional en su estado actual. Entre los más críticos se encuentran la exposición pública de credenciales de API de terceros en el repositorio, un secreto JWT con valor fallback codificado en el código fuente, modo DEBUG activo por defecto, CORS wildcard sin restricción de origen, y la ausencia de control de acceso en endpoints de administración de usuarios. Adicionalmente, se detectaron **cinco (5) hallazgos Altos**, **seis (6) Medios**, **cuatro (4) Bajos** y **dos (2) Informativos**.

**Veredicto: NO APTO PARA PRODUCCIÓN.** Se requiere corrección de todos los hallazgos Bloqueantes y Altos antes de cualquier proceso de recepción contractual.

### 1.1 Dashboard de Riesgo

```
┌─────────────────────────────────────────────────────┐
│              DASHBOARD DE RIESGO                    │
├──────────────┬──────────┬──────────┬────────────────┤
│ Bloqueantes  │  Altas   │  Medias  │ Bajas / Info   │
│      6       │    5     │    6     │   4  /   2     │
├──────────────┴──────────┴──────────┴────────────────┤
│ VEREDICTO GENERAL:  NO APTO PARA PRODUCCIÓN        │
└─────────────────────────────────────────────────────┘
```

### 1.2 Tabla Maestra de Hallazgos

| N°   | Sección    | Hallazgo                                                        | Severidad       | CVSS  | Estado  |
|------|------------|-----------------------------------------------------------------|-----------------|-------|---------|
| H-01 | 3. Seguridad | Clave API de servicio de IA expuesta en repositorio público   | Bloqueante 🔴   | 9.8   | Abierto |
| H-02 | 3. Seguridad | Secreto JWT hardcodeado como valor por defecto               | Bloqueante 🔴   | 9.1   | Abierto |
| H-03 | 3. Seguridad | CORS wildcard `*` activo como fallback de producción         | Bloqueante 🔴   | 8.8   | Abierto |
| H-04 | 3. Seguridad | Correos institucionales de funcionarios en repositorio público | Bloqueante 🔴  | 6.5   | Abierto |
| H-05 | 3. Seguridad | Ausencia de control de acceso por rol en CRUD de usuarios    | Bloqueante 🔴   | 9.9   | Abierto |
| H-06 | 5. Infraestr.| Modo DEBUG activo por defecto en producción                  | Bloqueante 🔴   | 7.5   | Abierto |
| H-07 | 4. SAST     | Inyección SQL por concatenación de nombre de tabla           | Alta 🟠         | 8.8   | Abierto |
| H-08 | 4. SAST     | Vulnerabilidad Zip Slip en endpoint de importación de volumen | Alta 🟠         | 9.0   | Abierto |
| H-09 | 3. Seguridad | Endpoints sensibles accesibles sin autenticación             | Alta 🟠         | 7.5   | Abierto |
| H-10 | 4. SAST     | Exposición de stack trace y detalles internos en respuestas  | Alta 🟠         | 5.3   | Abierto |
| H-11 | 3. Seguridad | Auto-registro público sin validación ni aprobación           | Alta 🟠         | 6.5   | Abierto |
| H-12 | 3. Seguridad | Token JWT almacenado en localStorage (XSS-accesible)         | Media 🟡        | 6.1   | Abierto |
| H-13 | 5. Infraestr.| IP del servidor hardcodeada en múltiples archivos frontend   | Media 🟡        | 5.3   | Abierto |
| H-14 | 5. Infraestr.| Endpoint `/health` expone información interna del sistema    | Media 🟡        | 5.3   | Abierto |
| H-15 | 5. Infraestr.| Ausencia total de cabeceras de seguridad HTTP                | Media 🟡        | 6.1   | Abierto |
| H-16 | 3. Seguridad | Sin rate limiting en endpoints de autenticación              | Media 🟡        | 7.5   | Abierto |
| H-17 | 5. Infraestr.| Datos de remuneraciones municipales en JSON estático público | Media 🟡        | 5.3   | Abierto |
| H-18 | 6. Higiene  | Archivos `.pyc` compilados versionados en el repositorio     | Baja 🟢         | N/A   | Abierto |
| H-19 | 6. Higiene  | Archivos de test y scripts residuales en producción          | Baja 🟢         | N/A   | Abierto |
| H-20 | 6. Higiene  | Función `cleanup_expired_sessions()` con código muerto       | Baja 🟢         | N/A   | Abierto |
| H-21 | 6. Higiene  | Ausencia de pipeline CI/CD con etapas de seguridad           | Baja 🟢         | N/A   | Abierto |
| H-22 | 7. Docs     | Documentación de API ausente (sin OpenAPI/Swagger)           | Informativo 🔵  | N/A   | Abierto |
| H-23 | 7. Docs     | Ausencia de política de contraseñas documentada              | Informativo 🔵  | N/A   | Abierto |

---

## 2. Objetivo y Metodología

### 2.1 Alcance de la Auditoría

**Componentes revisados:**
- Backend API: `backend/app21.py` (Flask, ~5.800 líneas), `backend/correo.py`, `backend/config_correo.json`, `backend/requirements.txt`
- Infraestructura: `Dockerfile`, `ngnix.config`, `.railwayignore`
- Frontend: todos los archivos HTML/JS bajo `frontend/`, incluyendo módulos de seguridad, SECPLAN, licitaciones y transparencia
- Base de datos: scripts SQL en `database/` (DDL, seeds, triggers)
- Repositorio: `.gitignore`, historial de commits, archivos de datos estáticos (`*.json`)
- Aplicación móvil: estructura en `movil/`

**Componentes excluidos:**
- Infraestructura de producción en Railway (no provista para análisis dinámico)
- Configuración de la base de datos en el host Railway (acceso no disponible)
- Pruebas dinámicas de penetración (fuera de alcance de auditoría estática)
- Módulo `backend/auditoria_engine.py` (referenciado pero no incluido en el repositorio al momento de la revisión)

**Commit revisado:** rama `main`, commit `a50f42e` (30 de marzo de 2026)

### 2.2 Metodología Aplicada

- **Revisión estática manual (SAST):** análisis línea a línea del backend Python y del JavaScript del frontend.
- **Análisis de dependencias:** revisión de `requirements.txt` contra versiones publicadas y CVEs conocidos.
- **Revisión de configuración:** Dockerfile, CORS, JWT, modo debug, variables de entorno.
- **Análisis de flujos de autenticación/autorización:** trazado de cada endpoint desde la recepción de la solicitud hasta la ejecución en base de datos.
- **Análisis de historial de commits:** detección de credenciales y datos sensibles en commits anteriores.
- **Revisión de datos estáticos:** archivos JSON en el frontend con posible contenido de PII.
- **Marcos de referencia:** OWASP Top 10 2021, OWASP ASVS 4.0, CWE Top 25, NIST SP 800-53, Ley 19.628 (Chile).

### 2.3 Herramientas Utilizadas

| Herramienta         | Uso                                                      |
|---------------------|----------------------------------------------------------|
| Análisis manual     | Revisión de código línea a línea con contexto semántico  |
| Git CLI             | Inspección de historial de commits y archivos rastreados |
| Python 3 (scripts)  | Decodificación de ofuscación, análisis de JSON estáticos |
| Grep / Find         | Búsqueda de patrones de vulnerabilidad en el repositorio |

### 2.4 Limitaciones

- Esta auditoría es **estrictamente estática**; no incluye pruebas de penetración dinámicas (DAST).
- No se auditó la infraestructura en Railway ni la configuración del servidor PostgreSQL en producción.
- El módulo `auditoria_engine.py` no estaba disponible en el repositorio para su revisión.
- La lógica de negocio no documentada no fue evaluada.
- No se realizó análisis de la aplicación móvil nativa más allá de su estructura estática.

---

## 3. Seguridad y Control de Acceso

### 3.1 Autenticación

El sistema implementa autenticación JWT (PyJWT 2.8.0) con algoritmo HS256 y expiración configurable a 24 horas. El flujo de login utiliza bcrypt para verificación de contraseñas (hallazgo positivo). Se implementa una blocklist JWT en base de datos para invalidación de sesiones al hacer logout. Sin embargo, se identificaron los hallazgos críticos H-01, H-02, H-11 y H-16 detallados a continuación.

### 3.2 Autorización y Control de Acceso

El sistema combina dos mecanismos: `nivel_acceso` numérico (0–20) y tabla `user_roles`. Sin embargo, la mayoría de los endpoints de gestión de usuarios **solo verifican que el usuario esté autenticado** (decorador `@session_required`) sin validar su nivel de acceso. Véase H-05.

### 3.3 Configuración CORS

Se identificó un fallback de configuración wildcard (`*`) como hallazgo H-03.

### 3.4 Protección contra CSRF

El sistema usa JWT por Bearer Token en cabecera `Authorization`, lo que mitiga el riesgo CSRF clásico para los endpoints de API. Sin embargo, el token también se almacena en `localStorage` y como cookie HttpOnly (doble almacenamiento inconsistente), y algunos archivos del frontend recuperan el token desde `localStorage` directamente, aumentando la superficie de ataque XSS. Véase H-12.

### 3.5 Gestión de Secretos y Credenciales

---

### H-01: Clave API de servicio de IA expuesta en repositorio público

**Severidad:** Bloqueante 🔴 | **CVSS v3.1:** 9.8 | **CWE:** CWE-798

- **Observación:** El archivo `frontend/division/seguridad/admin_general/js/ia.js` contiene una clave API del servicio ZhipuAI (BigModel) "ofuscada" mediante XOR con una semilla de texto plano. Tanto la cadena base64 codificada como la semilla de decodificación se encuentran en el mismo archivo JavaScript público, accesible a cualquier visitante del sitio. La clave decodificada es completamente operativa. Adicionalmente, el archivo `frontend/division/secplan/admin_general/chat.html` contiene en un comentario una clave API anterior del mismo servicio también en texto claro, y el mismo esquema de ofuscación reutilizable.

- **Evidencia:**
  ```javascript
  // Archivo: frontend/division/seguridad/admin_general/js/ia.js — Líneas 16–45
  const OFUSCADO = "VgAMFkZXBBFdUEpXQwFFXRZXA19NXV1XXQdQBVpDFlBIIwMkGxUkEgJcIRAXAUBcBQ==";
  getKey(seed) {
      const data = Uint8Array.from(atob(OFUSCADO), c => c.charCodeAt(0));
      // XOR con la semilla — ambas presentes en el mismo archivo
  }
  this.API_KEY = this.getKey("gfhrsdfsdfseweretfghtddfdf");
  // Clave decodificada: 1fdd53bb96924d78b1d799919a7c21e4.PgBhpSwp9Uvpi48a
  
  // Archivo: frontend/division/secplan/admin_general/chat.html — Línea 492
  //const API_KEY = "1dbcda64e67c4d31a7e9e5565efc5cae.M5ZIv5sFPbdOwgKw"; // clave anterior en claro
  const API_KEY = getKey("gfhrsdfsdfseweretfghtddfdf");
  ```
  Archivos: `frontend/division/seguridad/admin_general/js/ia.js` | `frontend/division/secplan/admin_general/chat.html`

- **Impacto:** Cualquier persona que acceda al repositorio público de GitHub o al código fuente del frontend puede decodificar la clave en segundos (verificado durante la auditoría). Un actor malicioso puede utilizar la clave para realizar peticiones ilimitadas al servicio de IA a expensas del titular, incurriendo en costes económicos significativos, agotar quotas de uso, y potencialmente acceder a datos procesados por el modelo si el servicio almacena conversaciones. El daño no se limita al sistema municipal: afecta directamente la cuenta de facturación del proveedor.

- **Referencia:** OWASP Top 10: A02:2021 – Cryptographic Failures | CWE-798: Use of Hard-coded Credentials | NIST SP 800-53: IA-5

- **Recomendación:** Revocar **de inmediato** ambas claves comprometidas en el panel de ZhipuAI (BigModel). Las claves de API de servicios externos jamás deben residir en código frontend ni en repositorios versionados. La arquitectura correcta es que el backend actúe como proxy: el frontend llama a un endpoint del backend propio (p. ej. `POST /api/ia/consulta`) que inyecta la clave desde una variable de entorno del servidor. Ejemplo de variable de entorno en Railway:
  ```bash
  # Railway → Variables de entorno
  ZHIPU_API_KEY=<nueva_clave>
  ```
  ```python
  # backend/app21.py
  import os
  ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
  # El frontend nunca recibe esta clave; solo llama al proxy backend
  ```

---

### H-02: Secreto JWT hardcodeado como valor por defecto en código fuente

**Severidad:** Bloqueante 🔴 | **CVSS v3.1:** 9.1 | **CWE:** CWE-798

- **Observación:** La línea 25 de `backend/app21.py` define el secreto de firma JWT con un valor fallback hardcodeado en texto claro dentro del código fuente, el cual es público en GitHub.

- **Evidencia:**
  ```python
  # backend/app21.py — Línea 25
  JWT_SECRET = os.getenv("JWT_SECRET_KEY", "fallback-secret-for-dev-123456")
  ```
  Archivo: `backend/app21.py` | Línea: 25

- **Impacto:** Si la variable de entorno `JWT_SECRET_KEY` no está configurada en el servidor de producción (condición no verificable externamente pero plausible dado el patrón de desarrollo observado), el secreto efectivo es `fallback-secret-for-dev-123456`, públicamente conocido. Un atacante puede firmar tokens JWT arbitrarios para cualquier `user_id`, incluyendo cuentas de administrador (nivel_acceso=20), obteniendo acceso total al sistema sin necesidad de credenciales. Este es un vector de escalada de privilegios completa.

- **Referencia:** OWASP Top 10: A02:2021 – Cryptographic Failures | CWE-798 | NIST SP 800-53: SC-12

- **Recomendación:** Eliminar el valor fallback. Si la variable no está configurada, el servidor debe negarse a iniciar:
  ```python
  JWT_SECRET = os.getenv("JWT_SECRET_KEY")
  if not JWT_SECRET:
      raise ValueError("JWT_SECRET_KEY no configurado. La aplicación no puede iniciar.")
  ```
  Generar un secreto criptográficamente seguro con `secrets.token_hex(64)` y almacenarlo como variable de entorno en Railway.

---

### H-03: CORS wildcard `*` activo como fallback de producción

**Severidad:** Bloqueante 🔴 | **CVSS v3.1:** 8.8 | **CWE:** CWE-942

- **Observación:** La configuración CORS en `backend/app21.py` permite todos los orígenes (`"*"`) cuando la variable de entorno `ALLOWED_ORIGINS` no está definida. Dado que también se habilita `supports_credentials=True`, la combinación es especialmente peligrosa. Un repositorio público con commits recientes no garantiza que las variables de entorno estén correctamente configuradas en Railway.

- **Evidencia:**
  ```python
  # backend/app21.py — Líneas 57–68
  allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "")
  if allowed_origins_raw:
      allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",")]
  else:
      allowed_origins = ["*"]  # Fallback: TODOS los orígenes permitidos
  
  CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)
  ```
  Archivo: `backend/app21.py` | Función: módulo principal | Líneas: 57–68

- **Impacto:** Si `ALLOWED_ORIGINS` no está configurada, cualquier dominio web puede realizar peticiones autenticadas a la API utilizando las credenciales del navegador de un usuario legítimo (ataque CSRF/CORS). Un sitio malicioso podría exfiltrar datos de proyectos, documentos o información de ciudadanos mientras el usuario municipal tiene una sesión activa.

- **Referencia:** OWASP Top 10: A05:2021 – Security Misconfiguration | CWE-942 | NIST SP 800-53: SC-8

- **Recomendación:** Eliminar el fallback a `"*"`. Si `ALLOWED_ORIGINS` no está configurada, usar una lista vacía que rechace todos los orígenes cruzados, o una lista restringida hardcodeada de dominios de producción conocidos:
  ```python
  PRODUCTION_ORIGINS = ["https://geoportalalgarrobo.github.io"]
  allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")] if allowed_origins_raw else PRODUCTION_ORIGINS
  ```

---

### H-04: Correos institucionales de funcionarios municipales versionados en repositorio público

**Severidad:** Bloqueante 🔴 | **CVSS v3.1:** 6.5 | **CWE:** CWE-312

- **Observación:** El archivo `backend/config_correo.json` contiene un mapeo de apellidos a direcciones de correo electrónico institucionales (`@munialgarrobo.cl`) de 15 funcionarios municipales identificados por nombre. Este archivo está versionado en el repositorio público de GitHub.

- **Evidencia:**
  ```json
  // backend/config_correo.json
  {
      "Araya": "saraya@munialgarrobo.cl",
      "Arriola": "carriola@munialgarrobo.cl",
      "Barrera": "gbarrera@munialgarrobo.cl",
      ...
      "Zambrano": "mzambrano@munialgarrobo.cl"
  }
  ```
  Archivo: `backend/config_correo.json`

- **Impacto:** La exposición de correos institucionales nominales en un repositorio público habilita ataques de spear-phishing dirigidos, enumeración de cuentas, y campañas de ingeniería social contra funcionarios municipales. Constituye además un tratamiento de datos personales sin las salvaguardas requeridas por la Ley 19.628 de Protección de la Vida Privada (Chile).

- **Referencia:** OWASP Top 10: A02:2021 | CWE-312 | Ley 19.628 Art. 9 (Chile)

- **Recomendación:** Remover inmediatamente el archivo del repositorio y de todo el historial git (`git filter-branch` o `git-filter-repo`). Almacenar el mapeo de correos como variable de entorno, en una tabla de la base de datos, o en un servicio de secrets management. Agregar `config_correo.json` al `.gitignore`.

---

### H-05: Ausencia de control de acceso por rol en endpoints de administración de usuarios

**Severidad:** Bloqueante 🔴 | **CVSS v3.1:** 9.9 | **CWE:** CWE-285

- **Observación:** Los endpoints `POST /users`, `PUT /users/<id>`, `DELETE /users/<id>`, `PUT /users/<id>/roles` y `PUT /users/<id>/reset-password` están protegidos únicamente por `@session_required` (cualquier usuario autenticado), sin verificar que el solicitante tenga un nivel de acceso o rol administrativo. En contraste, el endpoint `/api/admin/crear-funcionario` sí verifica `nivel_acceso >= 10`, demostrando que el equipo conocía el patrón pero no lo aplicó consistentemente.

- **Evidencia:**
  ```python
  # backend/app21.py — Líneas 685–725 (crear usuario)
  @app.route("/users", methods=["POST"])
  @session_required
  def create_user(current_user_id):
      # NO hay verificación de nivel_acceso ni de rol de admin
      data = request.get_json()
      hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
      cur.execute("INSERT INTO users ... nivel_acceso ...", (data["nivel_acceso"], ...))
      # Un usuario con nivel 0 puede crear un usuario con nivel_acceso=20 (admin)
  
  # backend/app21.py — Líneas 729–784 (actualizar usuario)
  @app.route("/users/<int:user_id>", methods=["PUT"])
  @session_required
  def update_user(current_user_id, user_id):
      allowed = {"nombre", "email", "nivel_acceso", "division_id", "activo", "password"}
      # Cualquier usuario autenticado puede escalar privilegios de cualquier otro usuario
  ```
  Archivo: `backend/app21.py` | Funciones: `create_user()`, `update_user()`, `delete_user()`, `set_user_roles()`, `reset_password()` | Líneas: 685–940

- **Impacto:** Un usuario con el nivel de acceso más bajo (vecino, nivel 0) puede enviar `PUT /users/1` con `{"nivel_acceso": 20}` y convertir su propia cuenta en administrador del sistema, o crear nuevas cuentas administrativas, o resetear la contraseña de cualquier funcionario. Esto comprende el control total de toda la plataforma, incluyendo datos de proyectos municipales, documentos y módulos de licitaciones.

- **Referencia:** OWASP Top 10: A01:2021 – Broken Access Control | CWE-285 | NIST SP 800-53: AC-3

- **Recomendación:** Crear un decorador `admin_required` que verifique `nivel_acceso >= 10` (o el rol `Administrador`) y aplicarlo a todos los endpoints sensibles de gestión de usuarios. Adicionalmente, impedir que un usuario modifique su propio `nivel_acceso`:
  ```python
  def admin_required(f):
      @wraps(f)
      def decorated(current_user_id, *args, **kwargs):
          conn = get_db_connection()
          with conn.cursor() as cur:
              cur.execute("SELECT nivel_acceso FROM users WHERE user_id = %s", (current_user_id,))
              row = cur.fetchone()
          release_db_connection(conn)
          if not row or row[0] < 10:
              return jsonify({"message": "No autorizado"}), 403
          return f(current_user_id, *args, **kwargs)
      return decorated
  ```

---

### H-06: Modo DEBUG activo por defecto en producción

**Severidad:** Bloqueante 🔴 | **CVSS v3.1:** 7.5 | **CWE:** CWE-94

- **Observación:** La línea 49 de `backend/app21.py` configura `DEBUG` leyendo la variable de entorno `FLASK_DEBUG` con valor por defecto `"True"`. Esto significa que si la variable no está explícitamente configurada como `"False"` o `"0"` en Railway, el servidor corre en modo debug activo.

- **Evidencia:**
  ```python
  # backend/app21.py — Línea 49
  DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("1", "true", "yes")
  ```
  Archivo: `backend/app21.py` | Línea: 49

- **Impacto:** El modo debug de Flask activa el Werkzeug Interactive Debugger, que expone un intérprete Python ejecutable en el navegador ante cualquier excepción no manejada. Un atacante que provoque cualquier error en la aplicación puede obtener ejecución remota de código (RCE) con los permisos del proceso servidor. Adicionalmente, el modo debug activa reloader automático y expone rutas internas.

- **Referencia:** OWASP Top 10: A05:2021 – Security Misconfiguration | CWE-94 | NIST SP 800-53: SI-10

- **Recomendación:** Cambiar el valor por defecto a `"False"`:
  ```python
  DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("1", "true", "yes")
  ```
  Y en Railway establecer explícitamente `FLASK_DEBUG=0`.

---

### 3.6 Manejo de Contraseñas

El sistema usa bcrypt con `gensalt()` por defecto (factor 12), lo que es adecuado. La contraseña se valida con una longitud mínima de 6 caracteres en el registro móvil. No existe política de contraseñas documentada ni enforced en el backend principal (endpoints `/users` y `/users/<id>/reset-password` no validan longitud ni complejidad). Véase H-23.

---

## 4. Análisis Estático de Código (SAST)

### 4.1 Inyección

---

### H-07: Inyección SQL por concatenación directa de nombre de tabla

**Severidad:** Alta 🟠 | **CVSS v3.1:** 8.8 | **CWE:** CWE-89

- **Observación:** La función auxiliar `crud_simple()` en `backend/app21.py` construye la query SQL concatenando directamente el parámetro `tabla` como string. De igual forma, `generic_delete()` concatena `table_name` en la sentencia UPDATE. Aunque en los usos actuales los valores son cadenas literales controladas por el desarrollador, el patrón es inherentemente peligroso y puede ser invocado con valores arbitrarios si el código es refactorizado.

- **Evidencia:**
  ```python
  # backend/app21.py — Línea 1943
  def crud_simple(tabla, current_user_id):
      conn = get_db_connection()
      with conn.cursor(...) as cur:
          cur.execute("SELECT * FROM " + str(tabla))  # Concatenación directa
  
  # backend/app21.py — Línea 2011
  def generic_delete(table_name, id):
      cur.execute("UPDATE " + str(table_name) + " SET activo = FALSE WHERE id = %s", (id,))
  ```
  Archivo: `backend/app21.py` | Funciones: `crud_simple()`, `generic_delete()` | Líneas: 1940–2015

- **Impacto:** Si un refactor futuro o una ruta de código no identificada permitiese pasar un valor controlado por el usuario como `tabla`, sería posible ejecutar consultas SQL arbitrarias contra la base de datos PostgreSQL (e.g., `areas; DROP TABLE users;--`). El patrón está documentado como práctica insegura estándar en cualquier lenguaje.

- **Referencia:** OWASP Top 10: A03:2021 – Injection | CWE-89 | NIST SP 800-53: SI-10

- **Recomendación:** Utilizar una lista blanca de nombres de tabla permitidos y rechazar cualquier valor fuera de ella:
  ```python
  ALLOWED_TABLES = {"areas", "financiamientos", "estados_postulacion", "sectores",
                    "lineamientos_estrategicos", "etapas_proyecto", "estados_proyecto"}
  
  def crud_simple(tabla, current_user_id):
      if tabla not in ALLOWED_TABLES:
          raise ValueError(f"Tabla no permitida: {tabla}")
      # psycopg2 no soporta parametrización de identificadores SQL con %s,
      # por lo que la lista blanca es el control correcto aquí.
      cur.execute(f"SELECT * FROM {tabla}")
  ```

---

### H-08: Vulnerabilidad Zip Slip en endpoint de importación de volumen

**Severidad:** Alta 🟠 | **CVSS v3.1:** 9.0 | **CWE:** CWE-22

- **Observación:** El endpoint `POST /api/volume/import` extrae un archivo ZIP subido por el usuario utilizando `zf.extractall(BASE_TARGET)` sin validar las rutas de los archivos contenidos en el ZIP. Un ZIP especialmente construido puede contener entradas con rutas relativas que incluyen `../` (path traversal), permitiendo escribir archivos en ubicaciones arbitrarias del sistema de archivos del contenedor.

- **Evidencia:**
  ```python
  # backend/app21.py — Líneas 5728–5730
  with zipfile.ZipFile(file) as zf:
      # Sin validación de nombres de archivo dentro del ZIP
      zf.extractall(BASE_TARGET)  # Zip Slip: un archivo "../../../etc/cron.d/backdoor" escribe fuera
  ```
  Archivo: `backend/app21.py` | Función: `volume_import()` | Líneas: 5725–5731

- **Impacto:** Un administrador (nivel_acceso >= 10) con acceso al endpoint puede, ya sea intencionalmente o al procesar un ZIP de origen no confiable, sobreescribir archivos críticos del sistema operativo dentro del contenedor, incluyendo scripts de inicio, archivos de configuración de la aplicación, o claves privadas. En el peor caso, permite ejecución remota de código si se sobreescribe un archivo Python cargado por la aplicación.

- **Referencia:** OWASP Top 10: A01:2021 – Broken Access Control | CWE-22 | CWE-434

- **Recomendación:**
  ```python
  import os
  def safe_extract(zf, path):
      for member in zf.infolist():
          member_path = os.path.realpath(os.path.join(path, member.filename))
          if not member_path.startswith(os.path.realpath(path) + os.sep):
              raise Exception(f"Intento de Zip Slip detectado: {member.filename}")
      zf.extractall(path)
  ```

---

### 4.2 Cross-Site Scripting (XSS)

No se identificaron usos de `innerHTML`, `dangerouslySetInnerHTML` ni `eval()` con datos de usuario en los archivos revisados. El frontend usa Vanilla JS con construcción de DOM por `innerHTML` en varios módulos, pero en los casos revisados los datos se insertan como texto, no como HTML. Se recomienda una revisión exhaustiva de todos los módulos de dashboard dado el volumen de archivos.

### 4.3 Gestión Insegura de Dependencias

Las dependencias en `backend/requirements.txt` tienen versiones fijas (positivo). Se destacan:
- `flask==3.0.0` — versión con soporte activo.
- `PyJWT==2.8.0` — versión con soporte activo.
- `bcrypt==4.1.2` — versión correcta para hashing de contraseñas.
- `Pillow==10.2.0` — versión con actualizaciones de seguridad disponibles; verificar CVEs en producción.

No existe archivo `poetry.lock` ni se observa escaneo automático de dependencias en CI/CD. Véase H-21.

### 4.4 Criptografía

No se identificaron algoritmos criptográficos débiles en el backend. bcrypt para contraseñas y HS256 para JWT son adecuados. La ofuscación XOR de claves API en el frontend (H-01) **no constituye criptografía** y debe ser tratada como texto plano expuesto.

### 4.5 Manejo de Errores y Logging

---

### H-10: Exposición de detalles de error interno al cliente

**Severidad:** Alta 🟠 | **CVSS v3.1:** 5.3 | **CWE:** CWE-209

- **Observación:** Múltiples endpoints en `backend/app21.py` retornan `str(e)` directamente en la respuesta JSON bajo el campo `"detail"`. Esto expone mensajes de error internos de Python, incluyendo nombres de tablas, columnas, rutas de archivo, y detalles del driver psycopg2, a cualquier usuario autenticado o no autenticado.

- **Evidencia:**
  ```python
  # backend/app21.py — patrón repetido en ~20 funciones, ejemplo en Línea 613
  except Exception as e:
      logger.error(f"Error en login: {e}")
      traceback.print_exc()
      return jsonify({"message": "Error interno", "detail": str(e)}), 500
  ```
  Archivo: `backend/app21.py` | Patrón repetido en líneas: 613, 643, 676, 723, 781, 1375, y otras ~15 ubicaciones.

- **Impacto:** Un atacante puede provocar errores intencionalmente (e.g., enviando parámetros inválidos) y obtener información sobre el esquema de la base de datos, rutas del sistema de archivos, o versiones de librerías, facilitando ataques más precisos.

- **Referencia:** OWASP Top 10: A05:2021 – Security Misconfiguration | CWE-209 | NIST SP 800-53: SI-11

- **Recomendación:** Retornar siempre un mensaje genérico al cliente y loguear el detalle internamente:
  ```python
  except Exception as e:
      logger.error(f"Error interno: {e}", exc_info=True)
      return jsonify({"message": "Error interno del servidor"}), 500
      # Nunca: return jsonify({"detail": str(e)})
  ```

---

### 4.6 Validación y Sanitización de Entradas

El endpoint `/api/mobile/auth/register` valida longitud mínima de contraseña (6 caracteres) pero no valida formato de email ni sanitiza el nombre de usuario. Los endpoints del backend principal no muestran validación de formato en campos como `email`, `nombre`, o `latitud`/`longitud`. El uso de consultas parametrizadas con psycopg2 en los endpoints principales mitiga el riesgo de SQL injection en esos puntos.

### 4.7 Exposición de Datos Sensibles

Véase H-14 (endpoint health) y H-17 (datos de remuneraciones en JSON estático).

### 4.8 Seguridad de APIs

---

### H-09: Endpoints sensibles accesibles sin autenticación

**Severidad:** Alta 🟠 | **CVSS v3.1:** 7.5 | **CWE:** CWE-306

- **Observación:** Los siguientes endpoints carecen del decorador `@session_required` y son accesibles sin autenticación, exponiendo datos municipales o de ciudadanos a cualquier usuario anónimo:
  - `GET /proyectos/<pid>/geomapas` — lista de mapas geoespaciales de proyectos (línea 2805)
  - `GET /proyectos/<pid>/observaciones` — lista de observaciones de proyectos (línea 3115)
  - `GET /api/mobile/reportes/todos` — todos los reportes ciudadanos con geolocalización, nombres y correos (línea 4126)
  - `GET /api/mobile/reportes/<rid>/comentarios` — comentarios de reportes (línea 4207)
  - `GET /api/mobile/reportes/<rid>/fotos` — fotos adjuntas a reportes ciudadanos (línea 4326)
  - `GET /api/licitaciones/docs/<filename>` — descarga directa de documentos de licitaciones (línea 1671)
  - `GET /api/licitaciones/lib/<filename>` — descarga de biblioteca de licitaciones (línea 1844)

- **Evidencia:**
  ```python
  # backend/app21.py — Líneas 2805–2844
  @app.route("/proyectos/<int:pid>/geomapas", methods=["GET"])
  # Sin @session_required
  def listar_geomapas_proyecto(pid):
      # Retorna datos geoespaciales de proyectos municipales sin autenticación
  
  # Líneas 4126–4150
  @app.route("/api/mobile/reportes/todos", methods=["GET"])
  # Sin @session_required — comentario: "Endpoint público para el mapa y admin"
  def get_todos_reportes():
      # Retorna nombres, emails y geolocalizaciones de reportantes ciudadanos
  ```

- **Impacto:** Los datos de geolocalización de reportes ciudadanos incluyen nombre, correo electrónico y ubicación precisa del incidente, con potencial de cruzarse para identificar a personas y sus domicilios. Los documentos de licitaciones pueden contener información comercial sensible. El acceso sin autenticación viola el principio de menor privilegio.

- **Referencia:** OWASP Top 10: A01:2021 – Broken Access Control | CWE-306 | Ley 19.628 Art. 9

- **Recomendación:** Agregar `@session_required` a todos los endpoints listados. Para los datos de geolocalización pública del mapa ciudadano, diseñar un endpoint específico que retorne únicamente los campos estrictamente necesarios (sin nombre ni email del reportante), disponible sin autenticación si el caso de uso lo requiere.

---

### H-11: Auto-registro público sin validación ni aprobación

**Severidad:** Alta 🟠 | **CVSS v3.1:** 6.5 | **CWE:** CWE-287

- **Observación:** El endpoint `POST /api/mobile/auth/register` permite a cualquier persona crear una cuenta en el sistema sin aprobación previa, sin validación de email, y con acceso automático al sistema como usuario activo (rol "Vecino"). No existe flujo de verificación de correo ni de aprobación administrativa.

- **Evidencia:**
  ```python
  # backend/app21.py — Líneas 3750–3800
  @app.route("/api/mobile/auth/register", methods=["POST"])
  def registrar():
      # Sin @session_required — público
      # Sin verificación de correo, sin aprobación
      c.execute("INSERT INTO users (..., activo) VALUES (%s, %s, %s, 0, TRUE) ...",
               (email, phash, nom))  # activo=TRUE inmediatamente
  ```
  Archivo: `backend/app21.py` | Función: `registrar()` | Líneas: 3750–3800

- **Impacto:** Un actor puede crear cuentas masivamente para reconocimiento del sistema, abusar de endpoints del módulo móvil que requieren autenticación, o intentar escalar privilegios aprovechando H-05.

- **Referencia:** OWASP Top 10: A07:2021 – Identification and Authentication Failures | CWE-287

- **Recomendación:** Implementar verificación de correo electrónico antes de activar la cuenta, o requerir aprobación manual de un administrador. Como mínimo, agregar rate limiting al endpoint de registro.

---

## 5. Infraestructura y Gobernanza de Datos

### 5.1 Base de Datos

El esquema SQL evidencia buen diseño relacional con uso de `SERIAL PRIMARY KEY`, claves foráneas y restricciones `CHECK`. El pool de conexiones psycopg2 está configurado con keepalives y timeout. No se identificó SQL injection en los endpoints que usan psycopg2 con parámetros `%s` correctamente, salvo H-07.

### 5.2 Configuración de Servidor y Contenedores

El Dockerfile usa multi-stage build (positivo para reducción de superficie). No se encontraron credenciales en capas del Dockerfile. El contenedor no especifica un usuario no-root, lo que significa que el proceso gunicorn corre como `root` dentro del contenedor.

### 5.3 Cabeceras de Seguridad HTTP

---

### H-15: Ausencia total de cabeceras de seguridad HTTP

**Severidad:** Media 🟡 | **CVSS v3.1:** 6.1 | **CWE:** CWE-693

- **Observación:** No se encontró configuración de ninguna cabecera de seguridad HTTP en `backend/app21.py` ni en `ngnix.config` (el archivo nginx presente está vacío). Las cabeceras `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy` y `Permissions-Policy` están completamente ausentes. Tampoco se suprime la cabecera `X-Powered-By` / `Server` que revela el stack tecnológico.

- **Evidencia:**
  ```bash
  # ngnix.config — vacío
  # No se encontró flask-talisman ni cabeceras manuales en app21.py
  grep -rn "X-Frame\|X-Content\|CSP\|Content-Security\|HSTS" backend/app21.py ngnix.config
  # Sin resultados
  ```
  Archivos: `backend/app21.py`, `ngnix.config`

- **Impacto:** La ausencia de CSP amplifica el riesgo de XSS. La ausencia de HSTS permite downgrade a HTTP. La ausencia de X-Frame-Options permite clickjacking. La exposición del servidor Flask y Gunicorn facilita ataques dirigidos a versiones conocidas.

- **Referencia:** OWASP Top 10: A05:2021 – Security Misconfiguration | CWE-693 | NIST SP 800-53: SC-8

- **Recomendación:** Usar `flask-talisman` para gestión centralizada de cabeceras:
  ```python
  from flask_talisman import Talisman
  Talisman(app, content_security_policy={
      'default-src': "'self'",
      'script-src': ["'self'", 'cdnjs.cloudflare.com'],
  }, force_https=True)
  ```

---

### H-13: IP del servidor hardcodeada en múltiples archivos del frontend

**Severidad:** Media 🟡 | **CVSS v3.1:** 5.3 | **CWE:** CWE-547

- **Observación:** La IP `186.67.61.251:8000` aparece hardcodeada en al menos 14 archivos HTML/JS del frontend, incluyendo un archivo de texto sin extensión (`frontend/promp`) que contiene el endpoint directamente como texto. Esto revela la dirección IP del servidor backend de producción públicamente.

- **Evidencia:**
  ```javascript
  // frontend/script/api.js — Línea 5
  BASE_URL: window.API_BASE_URL || "https://algarrobobase2-production-4ab9.up.railway.app",
  
  // frontend/documento.html
  const BASE_URL = "https://algarrobobase2-production-4ab9.up.railway.app";
  
  // Archivos adicionales: frontend/division/secplan/admin_general/chat.html,
  // frontend/division/secplan/admin_general/mapa.html, y 10+ archivos más
  ```
  Archivos: `frontend/script/api.js`, `frontend/documento.html`, y 12 archivos adicionales

- **Impacto:** La exposición de la IP del servidor de producción facilita ataques directos sin pasar por CDN o WAF, reconocimiento de puertos abiertos y ataques de denegación de servicio dirigidos.

- **Referencia:** CWE-547 | OWASP Top 10: A05:2021

- **Recomendación:** Centralizar la URL base en un único punto de configuración (ya existe `window.API_BASE_URL` como mecanismo de inyección) y reemplazar todas las ocurrencias hardcodeadas. En producción, usar nombre de dominio con certificado TLS en lugar de IP directa.

---

### H-14: Endpoint `/health` expone información interna del sistema

**Severidad:** Media 🟡 | **CVSS v3.1:** 5.3 | **CWE:** CWE-497

- **Observación:** El endpoint `GET /health` es accesible sin autenticación y retorna información detallada del sistema: estado del pool de conexiones, número mínimo y máximo de conexiones, hostname de la base de datos (porción post-`@` de la cadena de conexión), versión de la aplicación y flags de configuración.

- **Evidencia:**
  ```python
  # backend/app21.py — Líneas 444–506
  @app.route("/health")
  def health_check():  # Sin @session_required
      return jsonify({
          "database": {
              "status": db_status,
              "connection_string": DB_CONNECTION_STRING.split("@")[1]  # Expone host:puerto/db
          },
          "connection_pool": pool_status,  # min/max conexiones
          "version": "2.0.0",
      })
  ```
  Archivo: `backend/app21.py` | Función: `health_check()` | Líneas: 444–506

- **Impacto:** Expone el hostname y puerto del servidor PostgreSQL, la versión exacta de la aplicación y parámetros de configuración del pool. Esta información facilita ataques dirigidos.

- **Referencia:** CWE-497 | OWASP Top 10: A05:2021

- **Recomendación:** Requerir autenticación (o una API key de monitoreo) para el endpoint `/health`. Limitar la información expuesta a un simple `{"status": "ok"}` en el endpoint público.

---

### H-16: Ausencia de rate limiting en endpoints de autenticación

**Severidad:** Media 🟡 | **CVSS v3.1:** 7.5 | **CWE:** CWE-307

- **Observación:** Los endpoints `POST /auth/login` y `POST /api/mobile/auth/login` no implementan ningún mecanismo de limitación de intentos, bloqueo de cuentas, ni CAPTCHA. Un atacante puede realizar ataques de fuerza bruta de contraseñas de forma ilimitada.

- **Evidencia:**
  ```python
  # backend/app21.py — Línea 509
  @app.route("/auth/login", methods=["POST"])
  def login():
      # Sin rate limiting, sin contador de intentos fallidos, sin bloqueo
      if not bcrypt.checkpw(...):
          return jsonify({"message": "Credenciales inválidas"}), 401
      # No se registra el intento fallido de forma accionable
  ```
  Archivo: `backend/app21.py` | Funciones: `login()`, `login_mobile()` | Líneas: 509, 3855

- **Impacto:** Permite ataques de diccionario o fuerza bruta contra cuentas de funcionarios municipales, particularmente peligroso si los correos corporativos son conocidos (véase H-04).

- **Referencia:** OWASP Top 10: A07:2021 | CWE-307 | NIST SP 800-53: AC-7

- **Recomendación:** Implementar `flask-limiter` con límite de 5 intentos por minuto por IP para endpoints de login:
  ```python
  from flask_limiter import Limiter
  from flask_limiter.util import get_remote_address
  limiter = Limiter(app, key_func=get_remote_address)
  
  @app.route("/auth/login", methods=["POST"])
  @limiter.limit("5 per minute")
  def login():
      ...
  ```

---

### H-17: Datos de remuneraciones y registro municipal en JSON estático público

**Severidad:** Media 🟡 | **CVSS v3.1:** 5.3 | **CWE:** CWE-312

- **Observación:** El directorio `frontend/division/transparencia/admin_general/` contiene archivos JSON estáticos con datos desagregados de remuneraciones brutas, registro de personas y dotación de la Municipalidad de Algarrobo (archivo `MU001.json` en subdirectorios `remuneraciones_organismo2_all`, `personas_organismo2_all`, `registro_organismo2_all`), con información de cargo, grupo etario, sexo e importes mensuales desde 2023 hasta 2025.

- **Evidencia:**
  ```json
  // frontend/division/transparencia/admin_general/remuneraciones_organismo2_all/MU001.json
  // (primer registro)
  {"organismo_nombre": "Municipalidad de Algarrobo", "base": "Codigotrabajo",
   "homologado": "Asistente Social", "age_label": "30 a 50", "sexo": "mujer",
   "Mayo_2025": 353063, "Junio_2025": 532934 ...}
  ```
  Archivos: `frontend/division/transparencia/admin_general/remuneraciones_organismo2_all/MU001.json`, `personas_organismo2_all/MU001.json`, `registro_organismo2_all/MU001.json`

- **Impacto:** Aunque los datos están a nivel agregado (sin RUT ni nombre individual), la combinación de cargo, rango etario, sexo e importe mensual puede permitir re-identificación de funcionarios. Si se trata de datos del Portal de Transparencia (Ley 20.285), su publicación puede ser legal, pero el versionado en un repositorio público de código fuente no es el canal adecuado y puede incluir datos no aprobados para publicación pública.

- **Referencia:** Ley 19.628 Art. 9 (Chile) | Ley 20.285 (Transparencia) | CWE-312

- **Recomendación:** Evaluar si estos datos corresponden efectivamente al Portal de Transparencia (en cuyo caso deben publicarse a través del canal oficial, no del repositorio). Si no son datos de transparencia activa, removerlos del repositorio y servir desde un endpoint autenticado.

---

## 6. Higiene del Repositorio y Deuda Técnica

### 6.1 Archivos Residuales y Código Muerto

---

### H-19: Archivos de test y scripts residuales en código de producción

**Severidad:** Baja 🟢 | **CVSS v3.1:** N/A | **CWE:** N/A

- **Observación:** Se encontraron los siguientes archivos residuales en la rama principal del repositorio que no deben estar en un entorno de producción:
  - `frontend/division/secplan/admin_general/test.js`
  - `frontend/division/secplan/admin_general/test_script.js`
  - `frontend/promp` — archivo de texto sin extensión que contiene un endpoint de producción hardcodeado
  - `frontend/division/seguridad/admin_general/tools/inject_ia.js` y `inject_ia.py` — herramientas de inyección de IA
  - `frontend/division/seguridad/admin_general/scripts/update_footers.js`, `update_footers.py`, `update_vista2.js` — scripts de actualización masiva de HTML

- **Evidencia:**
  ```bash
  # frontend/promp (archivo de texto sin extensión)
  "tengo un endpoint https://algarrobobase2-production-4ab9.up.railway.app/proyectos"
  ```
  Archivos: `frontend/division/secplan/admin_general/test.js`, `frontend/promp`, y otros

- **Impacto:** Aumentan la superficie de ataque, exponen IPs internas, y dificultan la revisión del código en auditorías futuras.

- **Recomendación:** Eliminar todos los archivos de test, scripts de utilidades de desarrollo y archivos temporales de la rama principal. Usar ramas feature para trabajo en progreso.

---

### H-20: Función `cleanup_expired_sessions()` con código muerto y lógica rota

**Severidad:** Baja 🟢 | **CVSS v3.1:** N/A | **CWE:** CWE-1164

- **Observación:** La función `cleanup_expired_sessions()` está definida pero contiene código muerto: el `pass` hace que la función no haga nada, mientras que la docstring con la descripción de lo que debería hacer aparece como código huérfano debajo del `return` implícito. Esto indica que la lógica de limpieza nunca se ejecuta.

- **Evidencia:**
  ```python
  # backend/app21.py — Líneas ~298–310
  def cleanup_expired_sessions():
      pass
  
  
  
      """Limpia sesiones expiradas - llamar periódicamente"""
      # Este código nunca se ejecuta — la docstring está fuera de la función
  ```
  Archivo: `backend/app21.py`

- **Impacto:** La blocklist JWT nunca es purgada de tokens expirados, lo que puede causar crecimiento indefinido de la tabla `jwt_blocklist` y degradación de rendimiento en producción.

- **Recomendación:** Implementar la función correctamente o eliminarla junto con la docstring huérfana. Agregar una tarea periódica (cron job o background thread) que elimine entradas de `jwt_blocklist` con tokens cuya fecha `exp` haya vencido.

---

### H-18: Archivos `.pyc` compilados versionados en el repositorio

**Severidad:** Baja 🟢 | **CVSS v3.1:** N/A | **CWE:** N/A

- **Observación:** Se encontraron siete (7) archivos `.pyc` compilados de Python en `frontend/division/seguridad/admin_general/notebook/__pycache__/`, incluyendo versiones para Python 3.10 y 3.12. El `.gitignore` excluye `__pycache__/` correctamente, pero estos archivos fueron añadidos antes de que la regla existiera.

- **Evidencia:**
  ```
  frontend/division/seguridad/admin_general/notebook/__pycache__/proceso.cpython-312.pyc
  frontend/division/seguridad/admin_general/notebook/__pycache__/union.cpython-310.pyc
  ... (7 archivos total)
  ```

- **Impacto:** Los `.pyc` revelan la versión exacta de Python utilizada, pueden contener cadenas de constantes del código fuente y aumentan el tamaño del repositorio innecesariamente.

- **Recomendación:** Ejecutar `git rm -r --cached frontend/division/seguridad/admin_general/notebook/__pycache__/` y verificar que el `.gitignore` cubra este directorio.

---

### 6.2 Gitignore y Archivos Sensibles

El `.gitignore` está configurado correctamente para excluir `.env`, `*.pem`, `*.key` y `__pycache__/`. Sin embargo, no excluye `config_correo.json` (véase H-04) ni los archivos `.pyc` ya rastreados (véase H-18).

### 6.3 Calidad y Mantenibilidad del Código

El archivo `backend/app21.py` tiene aproximadamente 5.800 líneas en un único módulo, lo que dificulta el mantenimiento, la revisión de seguridad y el testing unitario. Se recomienda refactorizar en blueprints Flask separados por dominio funcional (auth, proyectos, licitaciones, mobile, control, auditoria).

### 6.4 Cobertura de Tests

**Cobertura estimada: Ausente (<5%).** Se encontraron únicamente dos archivos de test residuales en el frontend (`test.js`, `test_script.js`) que parecen scripts de prueba informal, no tests automatizados. No existe framework de testing (pytest, unittest) ni carpeta `tests/` en el backend.

### 6.5 Pipeline de CI/CD

---

### H-21: Ausencia de pipeline CI/CD con etapas de seguridad

**Severidad:** Baja 🟢 | **CVSS v3.1:** N/A | **CWE:** N/A

- **Observación:** No se encontró ningún archivo de configuración de pipeline (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`) en el repositorio. El despliegue a Railway parece ocurrir directamente desde la rama `main` sin gates de calidad.

- **Evidencia:** `find /repo -name "*.yml" -o -name "*.yaml" | grep -v .git` — sin resultados relevantes.

- **Impacto:** Sin CI/CD, no existe verificación automática de seguridad antes de desplegar. Cambios con vulnerabilidades pueden llegar a producción sin detección.

- **Recomendación:** Implementar GitHub Actions con al menos: escaneo de secretos (truffleHog o detect-secrets), análisis estático de Python (Bandit), auditoría de dependencias (pip-audit), y escaneo de imagen Docker (Trivy).

---

### 6.6 Gestión de Configuración por Entorno

Se detecta mezcla de configuración de desarrollo y producción (DEBUG por defecto `True`, fallback JWT, fallback CORS), lo que sugiere que el entorno de desarrollo es idéntico al de producción. Se recomienda usar perfiles de configuración explícitos (`DevelopmentConfig`, `ProductionConfig`) con validación de variables al arranque.

---

## 7. Documentación Técnica

### 7.1 Documentación de API

---

### H-22: Ausencia de especificación formal de API (OpenAPI/Swagger)

**Severidad:** Informativo 🔵 | **CVSS v3.1:** N/A | **CWE:** N/A

- **Observación:** No existe ninguna especificación OpenAPI, Swagger, RAML o Postman collection en el repositorio. El archivo `docs/TECHNICAL_DOC.md` describe algunos endpoints a alto nivel pero no cubre todos los parámetros, respuestas de error ni requisitos de autenticación.

- **Impacto:** Dificulta la mantención, la incorporación de nuevos desarrolladores y la realización de auditorías futuras. Impide la generación automática de clientes SDK.

- **Recomendación:** Implementar `flask-smorest` o `flasgger` para generación automática de OpenAPI desde los decoradores existentes de Flask.

---

### 7.2 Documentación de Arquitectura

El directorio `DOCUMENTACION/` contiene `README.md`, `INSTALACION.md` y `TECNOLOGIAS.md` con buena descripción general del sistema. Sin embargo, no incluye diagrama de arquitectura actualizado, diagrama entidad-relación de la base de datos ni Architecture Decision Records (ADRs).

### 7.3 Documentación Operacional

Existe una guía de instalación básica en `DOCUMENTACION/INSTALACION.md`. No se encontró un runbook de operación, procedimiento de disaster recovery, ni documentación de las variables de entorno requeridas con sus valores esperados.

### 7.4 Divergencias Documentación vs. Código

- El `README.md` referencia `backend/` como carpeta principal, pero el Dockerfile despliega desde `backend_railway/` (directorio no presente en el repositorio auditado).
- El `README.md` menciona `cp .env.example .env` pero no existe archivo `.env.example` en el repositorio.

---

## 8. Usabilidad, Accesibilidad y Diseño Responsivo

### 8.1 Responsividad Móvil

El sistema existe en dos interfaces paralelas: un frontend web para escritorio y una aplicación móvil en `movil/`. El frontend web usa Tailwind CSS (via CDN sin SRI — véase sección de cadena de suministro), lo que provee responsividad básica. Se detecta uso de `<meta name="viewport">` en las páginas revisadas.

### 8.2 Accesibilidad (A11y)

No se realizó un análisis exhaustivo de WCAG 2.1, pero el uso extensivo de componentes visuales sin alternativas textuales documentadas, y la estructura de dashboard con múltiples tablas de datos, sugiere que el cumplimiento de nivel AA no ha sido auditado ni documentado.

### 8.3 Rendimiento Frontend

Los scripts de Tailwind CSS, Chart.js, Leaflet y otras librerías se cargan desde CDNs externos sin atributos `integrity` y `crossorigin` (Subresource Integrity — SRI), lo que representa un riesgo de cadena de suministro de software (véase sección 10).

---

## 9. Alcance Contractual y Cumplimiento de Requerimientos

### 9.1 Funcionalidades Entregadas vs. Comprometidas

El repositorio evidencia un sistema funcional con los siguientes módulos claramente implementados: gestión de proyectos, licitaciones con workflow de 32 pasos, geomapas, documentos, hitos y observaciones, módulo de reportes ciudadanos (móvil), módulo de transparencia, módulo de seguridad comunal, panel de auditoría, módulo de control/trazabilidad y notificaciones por correo. No fue posible contrastar con el alcance contractual formal por falta de acceso a dicho documento.

### 9.2 Módulos Fuera de Alcance

Se detectaron los siguientes módulos/herramientas presentes en el código que podrían no formar parte del alcance contractual declarado:
- `frontend/division/transparencia/` — módulo completo de transparencia activa con datos de remuneraciones municipales
- `frontend/division/seguridad/` — módulo de seguridad comunal con análisis de delitos (datos CEAD)
- `/api/volume/import` y `/api/volume/export` — herramientas de migración y backup de datos
- `frontend/division/seguridad/admin_general/tools/inject_ia.js` — herramienta de inyección masiva de IA

### 9.3 Integraciones de Terceros No Declaradas

- **ZhipuAI (BigModel):** integración de IA para análisis de proyectos y chat. Servicio chino con política de privacidad bajo jurisdicción de RPC.
- **OpenStreetMap / Leaflet:** uso en módulos de mapa. Licencia ODbL, compatible con uso institucional.
- **Tailwind CSS CDN:** cargado desde CDN externo sin SRI.
- **Chart.js CDN:** cargado desde CDN externo sin SRI.
- **Railway.app:** plataforma de hosting, con datos potencialmente almacenados en jurisdicción extranjera.

### 9.4 Licencias de Software

Las dependencias Python identificadas (Flask, psycopg2, bcrypt, PyJWT, Pillow) usan licencias permisivas (BSD, MIT, Apache 2.0) compatibles con uso institucional. No se detectaron licencias copyleft restrictivas (GPL/AGPL).

---

## 10. Cadena de Suministro de Software (Supply Chain Security)

Las librerías JavaScript (Tailwind, Chart.js, Leaflet, jsPDF) se cargan desde CDNs externos sin atributos `integrity` y `crossorigin`. Un ataque de compromiso de CDN podría inyectar código malicioso en el frontend servido a todos los usuarios municipales sin ninguna detección. Se recomienda agregar SRI a todos los recursos de CDN externos:

```html
<!-- Ejemplo con SRI -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"
        integrity="sha384-[HASH]"
        crossorigin="anonymous"></script>
```

No se genera SBOM (Software Bill of Materials). No existen hooks de pre-commit para detección de secretos. No se encontraron firmas de commits ni protección de rama en el repositorio público.

---

## 11. Resiliencia y Continuidad Operacional

El sistema implementa un pool de conexiones a la base de datos con keepalives y manejo de reconexión, lo que es positivo para la resiliencia de conectividad. Se identifican los siguientes puntos de mejora:

- **Sin circuit breaker:** si el servicio de IA o el servicio de correo falla, no existe degradación controlada (graceful degradation).
- **Sin política de backup documentada:** no existe procedimiento de backup de la base de datos PostgreSQL en Railway ni RTO/RPO definidos.
- **SPOF:** el backend es un único proceso gunicorn en un único contenedor Railway, sin redundancia documentada.
- **Healthchecks:** el endpoint `/health` existe pero no hay evidencia de que Railway esté configurado para reiniciar el contenedor ante fallo.

---

## 12. Conclusión General y Veredicto Técnico

### 12.1 Síntesis de Riesgos

El Geoportal Municipal de Algarrobo es un sistema con una funcionalidad notable y un diseño general bien estructurado: usa bcrypt para contraseñas, JWT con blocklist, consultas parametrizadas en la mayor parte del backend, y logging de actividad. Sin embargo, presenta una serie de vulnerabilidades críticas que, en su estado actual, representan un riesgo inaceptable para la institución y los ciudadanos que interactúan con ella.

El hallazgo más urgente es la exposición pública de una clave API activa de un servicio de inteligencia artificial en el repositorio GitHub, que cualquier persona en internet puede decodificar en segundos. A esto se suma un secreto de firma JWT con valor por defecto conocido, lo que podría permitir que un atacante cree tokens de administrador sin credenciales. El modo debug activo por defecto puede exponer un intérprete Python remoto al primer error de producción. Y cualquier usuario con una cuenta —incluyendo vecinos registrados— puede técnicamente convertirse en administrador del sistema modificando su propio nivel de acceso.

Adicionalmente, correos institucionales de funcionarios municipales están expuestos en un repositorio público, lo que habilita campañas de phishing dirigidas. Datos de reportes ciudadanos con geolocalización y datos de contacto son accesibles sin autenticación, lo que contraviene los principios de la Ley 19.628.

### 12.2 Veredicto de Recepción

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        VEREDICTO TÉCNICO                                │
├──────────────────────────────────────────────────────────────────────────┤
│ [ ] APTO PARA PRODUCCIÓN                                                 │
│                                                                          │
│ [ ] CONDICIONADO — REQUIERE CORRECCIONES PREVIAS                         │
│                                                                          │
│ [X] NO APTO — REVISIÓN MAYOR REQUERIDA                                  │
│     Se identificaron 6 hallazgos Bloqueantes y 5 Altos que deben        │
│     resolverse antes de cualquier proceso de recepción contractual.     │
│     Tres de los hallazgos Bloqueantes (H-01, H-02, H-03) requieren     │
│     acción inmediata independientemente del estado contractual,         │
│     dado que el repositorio es público y el daño puede materializarse  │
│     en cualquier momento.                                               │
└──────────────────────────────────────────────────────────────────────────┘
```

### 12.3 Hoja de Ruta de Remediación

| Prioridad       | Hallazgos          | Plazo sugerido                    | Responsable sugerido         |
|-----------------|--------------------|-----------------------------------|------------------------------|
| Bloqueante 🔴   | H-01, H-02, H-03   | **Inmediato** (hoy / esta semana) | Proveedor                    |
| Bloqueante 🔴   | H-04, H-05, H-06   | Antes de recepción contractual    | Proveedor                    |
| Alta 🟠         | H-07, H-08, H-09   | 15 días desde recepción           | Proveedor                    |
| Alta 🟠         | H-10, H-11         | 15 días desde recepción           | Proveedor                    |
| Media 🟡        | H-12, H-13, H-14   | 30–60 días                        | Proveedor / Equipo TI        |
| Media 🟡        | H-15, H-16, H-17   | 30–60 días                        | Proveedor / Equipo TI        |
| Baja 🟢         | H-18, H-19, H-20, H-21 | Próximo ciclo de desarrollo   | Equipo TI                    |

### 12.4 Recomendaciones Estructurales

1. **Implementar un programa de DevSecOps:** integrar herramientas de escaneo automático (Bandit, pip-audit, truffleHog) en el pipeline de despliegue a Railway antes de que cualquier commit llegue a producción.

2. **Adoptar una política de secretos centralizada:** implementar Railway Secrets o un vault equivalente para todas las credenciales (JWT secret, claves de API de IA, strings de conexión), y establecer la regla de que ningún valor secreto puede estar en código fuente.

3. **Refactorizar el backend en módulos:** el archivo monolítico `app21.py` de ~5.800 líneas dificulta la auditoría, el testing y el mantenimiento. Dividirlo en blueprints Flask por dominio permite aplicar controles de acceso uniformes y facilita la detección de vulnerabilidades.

4. **Implementar pruebas de seguridad automatizadas:** crear suite de tests para flujos críticos de autenticación, autorización y validación de entradas. Incluir tests de regresión para cada vulnerabilidad corregida.

5. **Contratar auditorías periódicas y pentesting dinámico:** esta auditoría estática identifica vulnerabilidades en el código, pero no reemplaza un test de penetración dinámico (DAST) que valide el comportamiento del sistema en producción con herramientas como OWASP ZAP o Burp Suite.

### 12.5 Condiciones para Re-auditoría

Los siguientes hallazgos, una vez corregidos por el proveedor, requieren verificación técnica formal con evidencia antes de habilitar el pase a producción:

- **H-01:** Confirmación de revocación de claves ZhipuAI comprometidas + evidencia de que el frontend ya no contiene claves ni ofuscaciones de claves.
- **H-02:** Confirmación de que `JWT_SECRET_KEY` está configurada como secreto en Railway y el código no tiene fallback.
- **H-03:** Confirmación de que `ALLOWED_ORIGINS` está configurada con dominios explícitos y el código no tiene fallback a `"*"`.
- **H-05:** Revisión de todos los endpoints de gestión de usuarios con test de autorización que demuestre que un usuario con nivel 0 no puede modificar usuarios ni niveles de acceso.
- **H-08:** Revisión del código de importación de ZIP con demostración de que el path traversal es bloqueado.
- **H-09:** Confirmación de que los endpoints listados retornan 401 sin token válido.


