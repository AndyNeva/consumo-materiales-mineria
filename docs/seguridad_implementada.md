# Documentación de Seguridad — consumo-materiales-mineria

**Proyecto:** Sistema de Gestión de Consumo de Materiales (Planta de Hormigón)  
**Responsable:** Andrés Nevárez
**Fecha:** Junio 2026

---

## Resumen de tareas implementadas

| # | Tarea | Archivos modificados |
|---|---|---|
| 4 | Whitelist en `columnas_tabla` | `utils/db.py` |
| 5 | `secret_key` desde variables de entorno | `app.py` |
| 14 | Variables de entorno con `python-dotenv` | `utils/db.py`, `.env`, `.gitignore`, `.env.example` |
| 2 | Decorador `@login_required` | `auth/decoradores.py`, `app.py` |
| 6 | Headers de seguridad HTTP | `app.py` |
| 7 | Cookies de sesión seguras | `app.py` |
| 12 | Rate limiting en login | `app.py` |

---

## Estructura de archivos resultante

```
consumo-materiales-mineria/
├── auth/
│   ├── __init__.py
│   └── decoradores.py       ← login_required
├── utils/
│   └── db.py                ← whitelist + RUTA_BD desde .env
├── app.py                   ← config de seguridad centralizada
├── .env                     ← NO va a GitHub
├── .env.example             ← SÍ va a GitHub
└── .gitignore               ← incluye .env
```

---

## Tarea 4 — Whitelist en `columnas_tabla`

**Rama:** `fix/security-whitelist-columnas-tabla`  
**Archivo:** `utils/db.py`  
**Commit:** `fix(security): whitelist en columnas_tabla para prevenir SQLi por nombre de tabla`

### Problema
`PRAGMA table_info()` no acepta parámetros con `?`, por lo que la función usaba un f-string:

```python
# ANTES — vulnerable si tabla viniera de input externo
cursor.execute(f"PRAGMA table_info({tabla})")
```

### Solución

```python
# utils/db.py
_TABLAS_PERMITIDAS = frozenset({
    "despachos", "materiales", "usuarios",
    "recetas", "movimientos", "centros_costos", "zonas"
})

def columnas_tabla(conexion: sqlite3.Connection, tabla: str) -> List[str]:
    """
    Obtiene los nombres de columnas de una tabla.
    Usa whitelist para prevenir inyección SQL via nombre de tabla.
    """
    if tabla not in _TABLAS_PERMITIDAS:
        raise ValueError(f"Tabla '{tabla}' no permitida.")
    cursor = conexion.execute(f"PRAGMA table_info({tabla})")
    return [fila["name"] for fila in cursor.fetchall()]
```

### Beneficio
Si en el futuro alguien agrega un endpoint que llame `columnas_tabla` con input del usuario, la función lanza un error antes de tocar la base de datos.

---

## Grupo A — Variables de entorno y `secret_key`

**Rama:** `feature/security-variables-entorno`  
**Archivos:** `app.py`, `utils/db.py`, `.env`, `.env.example`, `.gitignore`  
**Commit:** `feat(security): variables de entorno y secret_key via python-dotenv`

### Dependencia agregada

```
# requirements.txt
python-dotenv>=1.0
```

### Archivos creados

**`.env`** — no va al repositorio:
```bash
SECRET_KEY=<generado con secrets.token_hex(32)>
DB_PATH=db/gestion_materiales.db
FLASK_ENV=development
FLASK_DEBUG=True
```

Para generar el `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**`.env.example`** — sí va al repositorio, sirve de plantilla para el equipo:
```bash
SECRET_KEY=genera_uno_con_secrets.token_hex_32
DB_PATH=db/gestion_materiales.db
FLASK_ENV=development
FLASK_DEBUG=True
```

**`.gitignore`** — entradas relevantes:
```
.env
__pycache__/
*.pyc
db/gestion_materiales.db
```

### Cambios en `utils/db.py`

```python
from dotenv import load_dotenv

load_dotenv()

RUTA_BD = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "gestion_materiales.db")
)
```

El segundo argumento de `os.getenv` es el fallback: si alguien corre el proyecto sin `.env`, no explota.

### Cambios en `app.py`

```python
load_dotenv()

app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY no definida. Revisa tu archivo .env")
```

El `raise RuntimeError` es intencional: si el servidor arranca sin `SECRET_KEY`, falla con un mensaje claro en lugar de correr inseguro en silencio.

### Beneficio
- `secret_key` deja de ser hardcodeada en código (necesaria para que Flask sessions funcionen de forma segura)
- La ruta de la BD es configurable por entorno
- El `.gitignore` evita que credenciales lleguen al repositorio accidentalmente
- El equipo sabe qué variables necesita gracias al `.env.example`

---

## Grupo C — Protección de rutas, headers, cookies y rate limiting

**Rama:** `feature/security-flask-config`  
**Archivos:** `auth/__init__.py`, `auth/decoradores.py`, `app.py`  
**Commit:** `feat(security): login_required en auth/decoradores, headers HTTP, cookies seguras y rate limiting`

### Dependencia agregada

```
# requirements.txt
flask-limiter>=3.5
```

---

### Tarea 2 — Decorador `@login_required`

**Archivo:** `auth/decoradores.py`

```python
from functools import wraps
from flask import session, request, redirect, url_for, jsonify


def login_required(f):
    """
    Decorador que protege rutas y endpoints API.
    - Rutas HTML: redirige a /login si no hay sesión activa.
    - Rutas API (/api/): devuelve JSON 401 si no hay sesión activa.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if "usuario_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "No autenticado"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated
```

Se separó en `auth/decoradores.py`para que Juan pueda importarlo en su módulo de login sin generar dependencia circular.

**Uso en `app.py`:**
```python
from auth.decoradores import login_required

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")
```

Rutas protegidas: `/dashboard`, `/registro`, `/inventario`, `/historial` y todos los endpoints `/api/`.

**Beneficio:** Cualquier intento de acceder directamente por URL sin sesión activa recibe un 401 (API) o redirección al login (HTML). Antes todas las rutas eran públicas.

---

### Tarea 6 — Headers de seguridad HTTP

**Archivo:** `app.py`

```python
@app.after_request
def agregar_headers_seguridad(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

| Header | Protege contra |
|---|---|
| `X-Frame-Options: DENY` | Clickjacking |
| `X-Content-Type-Options: nosniff` | MIME sniffing |
| `X-XSS-Protection: 1; mode=block` | XSS en navegadores legacy |
| `Referrer-Policy` | Filtración de URLs internas en headers |

Se aplican automáticamente a **todas** las respuestas del servidor.

---

### Tarea 7 — Cookies de sesión seguras

**Archivo:** `app.py`

```python
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "ph_session"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hora
```

| Configuración | Efecto |
|---|---|
| `HttpOnly` | JavaScript no puede leer la cookie → corta XSS → Session Hijacking |
| `SameSite: Lax` | Previene CSRF en la mayoría de casos |
| `PERMANENT_SESSION_LIFETIME` | Sesión expira en 1 hora de inactividad |

---

### Tarea 12 — Rate limiting en login

**Archivo:** `app.py`

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],       # sin límite global
    storage_uri="memory://"
)

@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")
def api_login():
    # Stub temporal — Juan reemplaza el cuerpo de esta función
    return jsonify({"ok": False, "error": "Login no implementado aún"}), 501
```

**Beneficio:** Máximo 5 intentos de login por minuto por IP. Un ataque de fuerza bruta queda frenado sin necesidad de bloquear usuarios legítimos.

> **Nota para Juan:** El stub `/api/login` ya tiene el rate limiter aplicado. Al implementar la autenticación real solo necesita reemplazar el cuerpo de la función; el límite ya está activo.

---

## Historial de commits

```
fix(security): whitelist en columnas_tabla para prevenir SQLi por nombre de tabla
feat(security): variables de entorno y secret_key via python-dotenv
feat(security): login_required en auth/decoradores, headers HTTP, cookies seguras y rate limiting
```

---

## Pendiente (requiere BD definida)

| # | Tarea | Bloqueada por |
|---|---|---|
| 1 | Autenticación real — endpoint `POST /api/login` | Definición de tabla `usuarios` |
| 3 | Hashing de contraseñas con Werkzeug | Definición de tabla `usuarios` |
| 9 | Roles de usuario | Definición de columna `rol` en `usuarios` |
| 8 | Errores sin información sensible | Por hacer |
| 13 | Logging de eventos de seguridad | Por hacer |
| 10 | Validación de input en backend | Por hacer |

