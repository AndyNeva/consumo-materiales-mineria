# Seguridad Implementada — Consumo de Materiales (Minería)

Documento vivo que describe el estado **actual** de las medidas de seguridad activas en
el proyecto. Reemplaza al log de implementación original (junio 2026); aquí se enumeran
las 18 controles que están efectivamente en producción, con el archivo responsable, los
parámetros clave y la justificación.

> **Convención**: cada control lleva (1) descripción, (2) dónde está implementado,
> (3) configuración / constantes relevantes, (4) evidencia (cómo verificarlo).

---

## Tabla de contenidos

- [1. Hashing de contraseñas](#1-hashing-de-contraseñas)
- [2. Longitud máxima de contraseña](#2-longitud-máxima-de-contraseña)
- [3. Política de complejidad de contraseña](#3-política-de-complejidad-de-contraseña)
- [4. `SECRET_KEY` desde entorno](#4-secret_key-desde-entorno)
- [5. Cookie de sesión endurecida](#5-cookie-de-sesión-endurecida)
- [6. Timeout de inactividad](#6-timeout-de-inactividad)
- [7. Rate limiting en `/api/login`](#7-rate-limiting-en-apilogin)
- [8. Bloqueo persistente anti-fuerza-bruta](#8-bloqueo-persistente-anti-fuerza-bruta)
- [9. Control de acceso por roles (RBAC)](#9-control-de-acceso-por-roles-rbac)
- [10. Protección CSRF global](#10-protección-csrf-global)
- [11. Headers de seguridad HTTP](#11-headers-de-seguridad-http)
- [12. Prevención de SQL injection](#12-prevención-de-sql-injection)
- [13. Validación de entradas](#13-validación-de-entradas)
- [14. Logging de seguridad](#14-logging-de-seguridad)
- [15. Mensajes de error genéricos](#15-mensajes-de-error-genéricos)
- [16. Ruta de base de datos configurable](#16-ruta-de-base-de-datos-configurable)
- [17. No exposición de datos sensibles](#17-no-exposición-de-datos-sensibles)
- [18. Pista de auditoría de inventario](#18-pista-de-auditoría-de-inventario)
- [Resumen de constantes de seguridad](#resumen-de-constantes-de-seguridad)
- [Pruebas de verificación](#pruebas-de-verificación)
- [Limitaciones conocidas y roadmap](#limitaciones-conocidas-y-roadmap)

---

## 1. Hashing de contraseñas

**Descripción**: las contraseñas nunca se almacenan en texto plano. Se aplica
`pbkdf2:sha256` con sal aleatoria mediante Werkzeug.

**Implementación**: `auth/login.py`

- `hashear_password(password)` → usa `werkzeug.security.generate_password_hash`.
- `verificar_password(password, password_hash)` → usa `check_password_hash`.
- Tanto `db/02_poblar_insumos.py` como `scripts/crear_usuarios.py` llaman a
  `hashear_password` al insertar los usuarios iniciales.

**Evidencia**:

```sql
SELECT username, password_hash FROM usuarios LIMIT 3;
-- admin | pbkdf2:sha256:600000$AbC123...$xyz...
```

El prefijo `pbkdf2:sha256:600000` indica el algoritmo, las iteraciones y la sal.

---

## 2. Longitud máxima de contraseña

**Descripción**: se rechazan contraseñas mayores a 128 caracteres antes de hashearlas.
Esto previene abuso de CPU por parte de un atacante que envíe contraseñas gigantescas
para causar DoS vía hashing costoso.

**Implementación**: `auth/login.py`

```python
MAX_LARGO_PASSWORD = 128
```

`hashear_password` lanza `ValueError("La contraseña excede el largo máximo")` si se
excede. El endpoint `/api/login` y la función `crear_usuario` propagan este error como
HTTP 400.

**Evidencia**:

```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d "{\"usuario\":\"admin\",\"password\":\"$(python -c 'print("a"*200)')\"}"
# → 400 Bad Request con mensaje sobre longitud
```

---

## 3. Política de complejidad de contraseña

**Descripción**: las contraseñas deben contener al menos **una letra, un número y un
símbolo**. Sin esta política, los usuarios tenderían a elegir `admin123` o similar.

**Implementación**: `auth/usuarios.py`

```python
def validar_password(password):
    errores = []
    if not password:
        errores.append("La contraseña no puede estar vacía.")
    if len(password) > MAX_LARGO_PASSWORD:
        errores.append(f"La contraseña no puede exceder {MAX_LARGO_PASSWORD} caracteres.")
    if password and not re.search(r"[A-Za-zÀ-ÿ]", password):
        errores.append("La contraseña debe tener al menos una letra.")
    if password and not re.search(r"\d", password):
        errores.append("La contraseña debe tener al menos un número.")
    if password and not re.search(r"[^\w\s]", password):
        errores.append("La contraseña debe tener al menos un símbolo.")
    return errores
```

La regex `[A-Za-zÀ-ÿ]` acepta letras con tildes y ñ. El frontend replica esta política
en `static/js/usuarios.js` con chips visuales (Letra / Número / Símbolo) que se
colorean en tiempo real mientras el usuario escribe.

**Evidencia**:

```bash
curl -X POST http://localhost:5000/api/usuarios \
  -H "X-CSRFToken: $TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"test","password":"abc","rol":"Operador"}'
# → 400 "La contraseña debe tener al menos un número y un símbolo."
```

---

## 4. `SECRET_KEY` desde entorno

**Descripción**: la clave de firma de sesiones Flask se carga desde la variable de
entorno `SECRET_KEY`. No hay fallback hardcoded.

**Implementación**: `app.py`

```python
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY no definida. Revisa tu archivo .env")
```

`python-dotenv` carga `.env` al arrancar (`load_dotenv()`). Si la clave falta, la app
no arranca. Esto evita que un despliegue con configuración por defecto firme sesiones
con un secreto público.

**Evidencia**: arrancar sin `.env` produce un traceback claro.

---

## 5. Cookie de sesión endurecida

**Descripción**: la cookie de sesión se configura con `HttpOnly` (JavaScript no la
lee), `SameSite=Lax` (mitiga CSRF cross-site) y un nombre opaco `ph_session` (no revela
tecnología).

**Implementación**: `app.py`

```python
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "ph_session"
```

**Evidencia**: en el navegador, DevTools → Application → Cookies muestra la cookie
`ph_session` con `HttpOnly` activo.

---

## 6. Timeout de inactividad

**Descripción**: si una sesión autenticada está inactiva más de 15 minutos, se cierra
automáticamente en el siguiente request.

**Implementación**: `app.py`

```python
INACTIVIDAD_MAX_SEGUNDOS = 15 * 60  # 15 minutos

@app.before_request
def verificar_inactividad():
    if "usuario_id" in session:
        ahora = time.time()
        ultima = session.get("ultima_actividad", ahora)
        if ahora - ultima > INACTIVIDAD_MAX_SEGUNDOS:
            session.clear()
        else:
            session["ultima_actividad"] = ahora
```

> **No confundir** con el bloqueo anti-fuerza-bruta (24 h, ver punto 8). El timeout de
> inactividad protege sesiones dejadas abiertas; el bloqueo protege contra intentos de
> login repetidos.

**Evidencia**: autenticarse, esperar 16 minutos, hacer un request → se recibe 401 y se
redirige a `/login`.

---

## 7. Rate limiting en `/api/login`

**Descripción**: el endpoint de login está limitado a **5 peticiones por minuto por
IP**. Esto frena ataques de diccionario incluso antes de que el bloqueo persistente
entre en juego.

**Implementación**: `app.py`

```python
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

@app.route("/api/login", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def api_login():
    ...
```

`storage_uri="memory://"` significa que el contador vive en memoria del proceso; si el
servidor se reinicia, el contador se reinicia, pero el bloqueo persistente (punto 8)
mantiene la protección.

**Evidencia**: 6 logins fallidos en menos de un minuto desde la misma IP → el 6°
recibe `429 Too Many Requests`.

---

## 8. Bloqueo persistente anti-fuerza-bruta

**Descripción**: tras **5 intentos fallidos** para el mismo par `username@ip`, la
cuenta se bloquea **24 horas**. El bloqueo se persiste en la tabla `intentos_login`,
así que **sobrevive reinicios del servidor** (a diferencia del rate limiter, que es
volátil).

**Implementación**: `auth/login.py` + tabla `intentos_login`.

Constantes:

```python
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 24 * 60 * 60   # 24 horas
```

Funciones clave:

- `_clave_intentos(username, ip)` → `"{username.lower()}@{ip}"`.
- `esta_bloqueado(username, ip)` → `(bool, segundos_restantes)` leyendo
  `intentos_login.bloqueado_hasta` (timestamp unix).
- `_registrar_fallo(username, ip)` → upsert en `intentos_login`; cuando
  `intentos >= MAX_INTENTOS`, setea `bloqueado_hasta = time.time() + BLOQUEO_SEGUNDOS`.
- `_limpiar_intentos(username, ip)` → `DELETE` de la fila tras login exitoso.

Esquema de la tabla (creada en `db/01_crear_esquema.py`):

```sql
CREATE TABLE intentos_login (
    clave TEXT PRIMARY KEY,                       -- "{username}@{ip}"
    intentos INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta REAL NOT NULL DEFAULT 0       -- timestamp unix
);
```

El endpoint `/api/login` devuelve:

- `401 Unauthorized` si las credenciales son incorrectas pero la cuenta no está
  bloqueada.
- `423 Locked` con `{"ok": false, "error": "Cuenta bloqueada. Intenta de nuevo en N segundos.", "bloqueado": true}` si la cuenta está bloqueada.

> **Justificación del par username+ip**: si se bloqueara solo por IP, un atacante
> rotando IPs seguiría intentando. Si se bloqueara solo por username, un atacante
> podría bloquear cuentas legítimas de otros usuarios. El par `username@ip` es el
> compromiso: el atacante solo se bloquea a sí mismo desde su IP, sin afectar al
> usuario real desde otra IP.

**Evidencia**: 5 logins fallidos desde la misma IP hacia el mismo usuario → el 6°
recibe `423 Locked`. Reiniciar el servidor y volver a intentar → el bloqueo sigue
activo.

**Desbloqueo manual** (operación de administración):

```bash
sqlite3 db/gestion_materiales.db "DELETE FROM intentos_login WHERE clave='usuario@1.2.3.4';"
```

---

## 9. Control de acceso por roles (RBAC)

**Descripción**: tres roles (`Admin`, `Operador`, `Visualizador`) con permisos
diferenciados. Cada ruta declara qué roles puede acceder mediante decoradores.

**Implementación**: `auth/roles.py`

```python
ROLES_VALIDOS = ("Admin", "Operador", "Visualizador")

def rol_requerido(*roles_permitidos):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if "usuario_id" not in session:
                # API: 401 JSON; HTML: redirect /login
                ...
            if session.get("rol") not in roles_permitidos:
                # API: 403 JSON; HTML: redirect /dashboard
                logger_seguridad.info(
                    "Acceso denegado | usuario=%s rol=%s ruta=%s ip=%s",
                    session.get("username"), session.get("rol"),
                    request.path, request.remote_addr
                )
                ...
            return vista(*args, **kwargs)
        return envoltura
    return decorador

solo_admin       = rol_requerido("Admin")
admin_u_operador = rol_requerido("Admin", "Operador")
cualquier_usuario = rol_requerido(*ROLES_VALIDOS)
```

Matriz de permisos por endpoint:

| Endpoint / Ruta                | Admin | Operador | Visualizador |
|--------------------------------|:-----:|:--------:|:------------:|
| `/dashboard`                   | ✅    | ✅       | ✅           |
| `/api/dashboard`               | ✅    | ✅       | ✅           |
| `/api/recetas`                 | ✅    | ✅       | ✅           |
| `/api/zonas`                   | ✅    | ✅       | ✅           |
| `/api/csrf-token`              | ✅    | ✅       | ✅           |
| `/api/alertas_consumo`         | ✅    | ✅       | ✅           |
| `/registro`                    | ✅    | ✅       | ❌           |
| `/api/despachos` (GET, POST)   | ✅    | ✅       | ❌           |
| `/api/historial_consumo`       | ✅    | ✅       | ❌           |
| `/api/resumen_consumo`         | ✅    | ✅       | ❌           |
| `/api/cruce_consumo_registro`  | ✅    | ✅       | ❌           |
| `/historial`                   | ✅    | ✅       | ❌           |
| `/inventario`                  | ✅    | ❌       | ❌           |
| `/api/materiales` (GET, POST)  | ✅    | ❌       | ❌           |
| `/usuarios`                    | ✅    | ❌       | ❌           |
| `/api/usuarios` (GET, POST)    | ✅    | ❌       | ❌           |
| `/login`, `/api/login`, `/logout` | (público) | (público) | (público) |

Cada denegación se registra en `seguridad.log` con usuario, rol, ruta e IP.

**Evidencia**: autenticarse como `visor` y llamar `GET /api/usuarios` → se recibe
`403 Forbidden` con `{"ok": false, "error": "No tienes permisos..."}`.

---

## 10. Protección CSRF global

**Descripción**: todos los formularios y POST JSON están protegidos contra Cross-Site
Request Forgery. El único exento es `/api/login` (necesario porque el usuario aún no
tiene sesión).

**Implementación**: `app.py`

```python
from flask_wtf import CSRFProtect
csrf = CSRFProtect(app)

@app.route("/api/login", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def api_login():
    ...
```

Frontend (`static/js/*.js`) obtiene el token vía `GET /api/csrf-token` y lo envía en el
header `X-CSRFToken` en cada POST. La plantilla `usuarios.html` además recibe el token
inyectado desde el servidor vía `{{ csrf_token }}`.

**Evidencia**: hacer un POST sin `X-CSRFToken` a `/api/despachos` → `400 Bad Request`
con mensaje "El token CSRF es inválido o falta".

---

## 11. Headers de seguridad HTTP

**Descripción**: todas las respuestas llevan headers de seguridad, y las rutas
protegidas además llevan headers anti-caché.

**Implementación**: `app.py` (decorador `@app.after_request`)

```python
@app.after_request
def agregar_headers_seguridad(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    rutas_protegidas = ("/dashboard", "/registro", "/inventario", "/historial", "/ml")
    if request.path in rutas_protegidas or request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response
```

| Header                  | Función                                                                |
|-------------------------|------------------------------------------------------------------------|
| `X-Frame-Options: DENY` | Clickjacking: la página no puede ser embebida en `<iframe>`.           |
| `X-Content-Type-Options: nosniff` | El navegador no intenta adivinar el MIME (evita XSS por archivo mal tipado). |
| `X-XSS-Protection: 1; mode=block` | Activa el filtro XSS del navegador (legacy, pero sigue siendo útil). |
| `Referrer-Policy: strict-origin-when-cross-origin` | No filtra query strings al referenciar a otros dominios. |
| `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` | Evita que datos sensibles queden en caché del navegador. |
| `Pragma: no-cache` | Equivalente HTTP/1.0 para retrocompatibilidad. |

**Evidencia**: `curl -I http://localhost:5000/api/dashboard` muestra todos los headers.

---

## 12. Prevención de SQL injection

**Descripción**: todas las consultas usan `?` placeholders (parameter binding) en lugar
de concatenar strings. Adicionalmente, `PRAGMA table_info` (que es la única consulta
que no puede usar `?` para el nombre de tabla) está detrás de una whitelist.

**Implementación**:

- Todos los DAOs (`services/*.py`, `auth/login.py`, `auth/usuarios.py`) usan
  `cursor.execute("SELECT ... WHERE x = ?", (valor,))`.
- `utils/db.py`:

```python
_TABLAS_PERMITIDAS = frozenset({
    "despachos", "materiales", "usuarios", "recetas", "movimientos",
    "centros_costos", "zonas",
    "Produccion_Diaria", "Produccion_Insumos", "Insumos",
    "Disenos_Mezcla", "Receta_Detalle", "Zonas", "Centros_Costo",
    "intentos_login", "Turnos"
})

def columnas_tabla(conexion, tabla):
    if tabla not in _TABLAS_PERMITIDAS:
        raise ValueError(f"Tabla no permitida: {tabla}")
    cursor = conexion.cursor()
    cursor.execute(f"PRAGMA table_info({tabla})")
    return [fila["name"] for fila in cursor.fetchall()]
```

**Evidencia**: intentar inyectar `' OR 1=1 --` como username en `/api/login` no
funciona; la consulta parametrizada lo trata como un string literal.

---

## 13. Validación de entradas

**Descripción**: todos los datos que entran por la API se validan antes de tocar la
base de datos. Las validaciones son tanto de tipo como de rango.

**Implementación**: `app.py` + `auth/usuarios.py`

| Dato                       | Validación                                                                                       |
|----------------------------|--------------------------------------------------------------------------------------------------|
| `fecha` (despachos, cruce) | ISO `YYYY-MM-DD` vía `datetime.strptime`                                                          |
| `volumen_m3`               | Float (admite coma decimal vía `_float_flexible`), > 0                                            |
| `arena_humedad_pct`        | Float entre 4 y 10 (si viene)                                                                     |
| `asentamiento_final_cm`    | Float entre 15 y 30 (si viene)                                                                    |
| `temperatura_c`            | Float entre -10 y 50 (si viene)                                                                   |
| `unidad` (materiales)      | Whitelist: `kg`, `l`, `m3`, `unidad`                                                              |
| `stock_*`                  | No negativo (`numero_no_negativo`)                                                                |
| `stock_maximo`             | >= `stock_minimo` (si ambos vienen)                                                               |
| `nombre` (material)        | No vacío, no solo dígitos, UNIQUE                                                                 |
| `username`                 | 1-50 caracteres, UNIQUE case-insensitive (validado en `validar_datos_usuario`)                    |
| `password`                 | Complejidad (ver punto 3) + longitud (ver punto 2)                                                |
| `rol`                      | Whitelist: `Admin`, `Operador`, `Visualizador`                                                    |
| `turno`                    | No vacío; se mapea a `id_turno` (1 = Diurno, 2 = Nocturno)                                        |
| `diseno_mezcla`, `wbs`, `zona` | No vacíos                                                                                    |

**Evidencia**: enviar `"volumen_m3": "-5"` a `/api/despachos` → `400 Bad Request` con
`"El volumen_m3 debe ser mayor que 0."`.

---

## 14. Logging de seguridad

**Descripción**: logger dedicado que escribe a `seguridad.log` (UTF-8) y stdout. Registra
eventos relevantes para auditoría: logins, bloqueos, denegaciones de rol, creación de
despachos, ajustes de inventario.

**Implementación**: `utils/logging_seguridad.py`

```python
import logging

def configurar_logging():
    handler_archivo = logging.FileHandler("seguridad.log", encoding="utf-8")
    handler_consola = logging.StreamHandler()
    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler_archivo.setFormatter(formato)
    handler_consola.setFormatter(formato)
    logger = logging.getLogger("seguridad")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler_archivo)
    logger.addHandler(handler_consola)

logger_seguridad = logging.getLogger("seguridad")
```

Eventos registrados (no exhaustivo):

- Login exitoso: `"Login OK | usuario=X ip=Y"`
- Login fallido: `"Login fallido | usuario=X ip=Y motivo=..."`
- Cuenta bloqueada: `"Cuenta bloqueada | usuario=X ip=Y intentos=5"`
- Denegación de rol: `"Acceso denegado | usuario=X rol=Y ruta=Z ip=..."`
- Despacho creado: `"Despacho creado | id=X usuario=Y ip=Z"`
- Despacho rechazado por validación: `"Despacho rechazado por validación | usuario=X ip=Y errores=[...]"`
- Material actualizado: `"Material actualizado | id=X usuario=Y ip=Z datos={...}"`
- Logout: `"Logout | usuario=X ip=Y"`

**Evidencia**: `tail -f seguridad.log` mientras se hace login muestra los eventos en
tiempo real.

> ⚠️ El log no rota automáticamente. En producción debe configurarse `RotatingFileHandler`
> o logrotate del SO para evitar crecimiento indefinido (ver roadmap).

---

## 15. Mensajes de error genéricos

**Descripción**: cuando ocurre una excepción inesperada, el cliente recibe un mensaje
fijo genérico; el traceback completo solo va al log. Esto evita filtrar información
sensible (rutas, nombres de tablas, fragmentos de SQL) al cliente.

**Implementación**: `app.py`

```python
MSG_ERROR_GENERICO = "Ocurrió un error al procesar la solicitud. Intenta de nuevo más tarde."
```

Cada handler de API usa `logging.exception(...)` (que incluye el traceback en el log) y
devuelve `{"ok": false, "error": MSG_ERROR_GENERICO}` con HTTP 500.

**Evidencia**: provocar un error interno (por ejemplo, eliminando la BD) y llamar
`/api/dashboard` → se recibe el mensaje genérico, pero `seguridad.log` contiene el
traceback completo.

---

## 16. Ruta de base de datos configurable

**Descripción**: la ruta de la BD se carga desde `DB_PATH` (con fallback a
`db/gestion_materiales.db`), permitiendo despliegues donde la BD vive en otro volumen.

**Implementación**: `utils/db.py`

```python
RUTA_BD = os.getenv("DB_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "db", "gestion_materiales.db"
))
```

El archivo `.env` se ignora en el control de versiones (debe estar en `.gitignore`).
Esto permite que cada entorno (dev, staging, prod) tenga su propia configuración sin
tocar código.

**Evidencia**: `DB_PATH=/tmp/test.db python app.py` usa esa BD en lugar de la default.

---

## 17. No exposición de datos sensibles

**Descripción**: las funciones de listado no devuelven columnas sensibles. En
particular, `password_hash` nunca llega al cliente.

**Implementación**: `auth/usuarios.py`

```python
def listar_usuarios(ruta_bd=RUTA_BD):
    with conectar(ruta_bd) as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT id, username, rol FROM usuarios ORDER BY id")
        return [dict(fila) for fila in cursor.fetchall()]
```

El SELECT explícito (en lugar de `SELECT *`) asegura que aunque se agreguen columnas
sensibles en el futuro, no se filtrarían accidentalmente.

**Evidencia**: `GET /api/usuarios` solo devuelve `id`, `username`, `rol`.

---

## 18. Pista de auditoría de inventario

**Descripción**: todo cambio de stock (alta, descuento por despacho, ajuste manual)
queda registrado en la tabla `movimientos` con `usuario_id`, `id_insumo`, `cantidad`,
`fecha` y `tipo`.

**Implementación**: `services/inventario.py` + `services/despachos.py`

```python
# services/inventario.py
def registrar_movimiento(conexion, usuario_id, id_insumo, cantidad, tipo, fecha=None):
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO movimientos (usuario_id, id_insumo, cantidad, fecha, tipo) "
        "VALUES (?, ?, ?, ?, ?)",
        (usuario_id, id_insumo, cantidad, fecha or datetime.now().isoformat(), tipo)
    )
```

Tipos de movimiento:

- `INGRESO` — al crear un material con `stock_actual > 0`.
- `EGRESO` — al registrar un despacho (descuento de insumos consumidos).
- `AJUSTE` — al editar `stock_actual` de un material existente.

Cada movimiento queda asociado al `usuario_id` de la sesión, dando trazabilidad total
de "quién hizo qué, cuándo y cuánto".

**Evidencia**:

```sql
SELECT m.id, u.username, i.nombre_insumo, m.cantidad, m.tipo, m.fecha
FROM movimientos m
JOIN usuarios u ON m.usuario_id = u.id
JOIN Insumos i ON m.id_insumo = i.id_insumo
ORDER BY m.fecha DESC
LIMIT 10;
```

---

## Resumen de constantes de seguridad

| Constante                       | Valor         | Archivo            |
|---------------------------------|---------------|--------------------|
| `MAX_LARGO_PASSWORD`            | 128           | `auth/login.py`    |
| `MAX_LARGO_USERNAME`            | 50            | `auth/usuarios.py` |
| `MAX_INTENTOS`                  | 5             | `auth/login.py`    |
| `BLOQUEO_SEGUNDOS`              | 86400 (24 h)  | `auth/login.py`    |
| `INACTIVIDAD_MAX_SEGUNDOS`      | 900 (15 min)  | `app.py`           |
| Rate limit `/api/login`         | 5 per minute  | `app.py`           |
| `ROLES_VALIDOS`                 | `Admin`, `Operador`, `Visualizador` | `auth/roles.py`, `auth/login.py` |
| `_TABLAS_PERMITIDAS`            | 16 tablas     | `utils/db.py`      |
| `SESSION_COOKIE_HTTPONLY`       | `True`        | `app.py`           |
| `SESSION_COOKIE_SAMESITE`       | `Lax`         | `app.py`           |
| `SESSION_COOKIE_NAME`           | `ph_session`  | `app.py`           |

---

## Pruebas de verificación

### Login correcto

```bash
curl -c cookies.txt -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","password":"Admin123!"}'
# 200 OK + cookie ph_session
```

### Login incorrecto 5 veces → 6° recibe 423

```bash
for i in 1 2 3 4 5 6; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:5000/api/login \
    -H "Content-Type: application/json" \
    -d '{"usuario":"admin","password":"MALA"}'
done
# 401 401 401 401 401 423
```

### Rate limit (6 logins en menos de 1 minuto)

```bash
for i in 1 2 3 4 5 6; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:5000/api/login \
    -H "Content-Type: application/json" \
    -d '{"usuario":"usuarioDistinto","password":"x"}'
done
# 401 401 401 401 401 429
```

### CSRF sin token

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/despachos \
  -H "Content-Type: application/json" \
  -d '{"fecha":"2025-07-08","volumen_m3":"10","diseno_mezcla":"UCEM-HE","turno":"Diurno","wbs":"WBS-1","zona":"ZONA_NORTE"}'
# 400 Bad Request (token CSRF faltante)
```

### Denegación de rol

```bash
# Autenticar como visor
curl -c cookies.txt -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"visor","password":"Visor123!"}'

# Intentar GET /api/usuarios (solo Admin)
curl -b cookies.txt http://localhost:5000/api/usuarios
# 403 Forbidden
```

### Headers de seguridad

```bash
curl -I -b cookies.txt http://localhost:5000/api/dashboard | grep -E "X-Frame|X-Content|Referrer|Cache-Control"
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# Referrer-Policy: strict-origin-when-cross-origin
# Cache-Control: no-store, no-cache, must-revalidate, max-age=0
```

---

## Limitaciones conocidas y roadmap

### Limitaciones actuales

1. **Sin HTTPS obligatorio**: la app escucha en HTTP plano. En producción debe ir
   detrás de un reverse proxy (Nginx/Caddy) con TLS.
2. **Sin rotación de logs**: `seguridad.log` crece indefinidamente. Programar
   `RotatingFileHandler` o logrotate.
3. **Rate limiter en memoria**: si se ejecutan múltiples workers (gunicorn -w 4), cada
   worker tiene su propio contador. Para producción multiworker, migrar a
   `storage_uri="redis://..."`.
4. **Sin expiración de sesiones absoluta**: solo hay timeout de inactividad (15 min).
   Falta un máximo absoluto (por ejemplo, 8 h) para forzar re-login diario.
5. **`intentos_login` no se purga automáticamente**: las filas viejas (con
   `bloqueado_hasta` expirado) permanecen en la tabla hasta que se hace un nuevo
   intento. Programar una limpieza periódica.
6. **Sin 2FA**: no hay segundo factor. Útil si el sistema se expone a Internet.

### Roadmap de seguridad

- [ ] Forzar HTTPS vía `Strict-Transport-Security` (HSTS) en el reverse proxy.
- [ ] Migrar rate limiter a Redis para soportar múltiples workers.
- [ ] Añadir `RotatingFileHandler` para `seguridad.log` (10 MB × 5 backups).
- [ ] Implementar expiración absoluta de sesión (8 h) además del timeout de
      inactividad.
- [ ] Añadir Content-Security-Policy estricta (sin `unsafe-inline`).
- [ ] Auditoría periódica de `movimientos` (script que detecte patrones anómalos).
- [ ] Soporte opcional de 2FA TOTP para usuarios Admin.
