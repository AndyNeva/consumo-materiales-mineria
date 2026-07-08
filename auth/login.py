"""
Lógica de autenticación del sistema.

Responsable: Juan Ruiz (@eljuandaruiz) — módulo de autenticación.

Aquí vive todo lo relacionado con verificar credenciales:
- Hash y verificación de contraseñas con Werkzeug (viene con Flask).
- Límite de longitud de contraseña (anti abuso de recursos al hashear).
- Límite de intentos fallidos con bloqueo temporal por usuario/IP.
- Consultas SIEMPRE parametrizadas (sin concatenar strings) -> anti SQL injection.

Las medidas de cabeceras HTTP, rate limiting general y SECRET_KEY las maneja
el líder del proyecto en app.py; aquí solo se COMPLEMENTAN.
"""

from __future__ import annotations

import time
from werkzeug.security import generate_password_hash, check_password_hash

from utils.db import conectar

# ---------------------------------------------------------------------------
# Configuración del módulo
# ---------------------------------------------------------------------------

# Longitud máxima de contraseña aceptada antes de hashear.
# Werkzeug no tiene el límite de 72 bytes de bcrypt, pero igual rechazamos
# entradas absurdamente largas para no gastar CPU hasheando textos enormes.
MAX_LARGO_PASSWORD = 128

# Control de intentos fallidos de login.
MAX_INTENTOS = 5            # intentos permitidos antes de bloquear
BLOQUEO_SEGUNDOS = 15 * 60  # 15 minutos de bloqueo

# Roles válidos del sistema (debe coincidir con auth/roles.py).
ROLES_VALIDOS = ("Admin", "Operador", "Visualizador")

# Registro en memoria de intentos fallidos.
# clave -> {"intentos": int, "bloqueado_hasta": float (timestamp)}
# Es suficiente para un proyecto universitario de un solo proceso.
# Si en el futuro se corre con varios workers, esto debería ir a la BD o Redis.
_intentos_fallidos: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Hash de contraseñas
# ---------------------------------------------------------------------------

def hashear_password(password: str) -> str:
    """
    Genera un hash seguro de la contraseña.

    Lanza ValueError si la contraseña excede MAX_LARGO_PASSWORD, para
    evitar hashear entradas gigantes (ataque de consumo de recursos).
    """
    if password is None or len(password) > MAX_LARGO_PASSWORD:
        raise ValueError(
            f"La contraseña no puede superar {MAX_LARGO_PASSWORD} caracteres."
        )
    return generate_password_hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña en texto plano contra su hash almacenado."""
    if not password or not password_hash:
        return False
    return check_password_hash(password_hash, password)


# ---------------------------------------------------------------------------
# Control de intentos fallidos / bloqueo temporal
# ---------------------------------------------------------------------------

def _clave_intentos(username: str, ip: str) -> str:
    """Construye la clave de seguimiento por usuario + IP."""
    return f"{(username or '').lower()}@{ip or 'desconocida'}"


def esta_bloqueado(username: str, ip: str) -> tuple[bool, int]:
    """
    Indica si la combinación usuario/IP está bloqueada.

    Returns:
        (bloqueado, segundos_restantes)
    """
    registro = _intentos_fallidos.get(_clave_intentos(username, ip))
    if not registro:
        return False, 0

    bloqueado_hasta = registro.get("bloqueado_hasta", 0)
    restante = int(bloqueado_hasta - time.time())
    if restante > 0:
        return True, restante

    return False, 0


def _registrar_fallo(username: str, ip: str) -> None:
    """Suma un intento fallido y activa el bloqueo si se pasa del límite."""
    clave = _clave_intentos(username, ip)
    registro = _intentos_fallidos.get(clave, {"intentos": 0, "bloqueado_hasta": 0})
    registro["intentos"] += 1

    if registro["intentos"] >= MAX_INTENTOS:
        registro["bloqueado_hasta"] = time.time() + BLOQUEO_SEGUNDOS

    _intentos_fallidos[clave] = registro


def _limpiar_intentos(username: str, ip: str) -> None:
    """Borra el historial de intentos tras un login exitoso."""
    _intentos_fallidos.pop(_clave_intentos(username, ip), None)


# ---------------------------------------------------------------------------
# Acceso a la base de datos (consultas parametrizadas)
# ---------------------------------------------------------------------------

def asegurar_columna_password(conexion) -> None:
    """Asegura que la tabla usuarios tenga la columna password_hash."""
    cursor = conexion.cursor()
    cursor.execute("PRAGMA table_info(usuarios)")
    columnas = [fila["name"] for fila in cursor.fetchall()]

    if "password_hash" not in columnas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN password_hash TEXT")


def buscar_usuario(username: str) -> dict | None:
    """
    Busca un usuario por username usando consulta PARAMETRIZADA.

    El '?' evita SQL injection: el valor nunca se concatena en el SQL.
    Devuelve un dict con id, username, rol y password_hash, o None.
    """
    with conectar() as conexion:
        asegurar_columna_password(conexion)
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, username, rol, password_hash "
            "FROM usuarios WHERE username = ?",
            (username,),
        )
        fila = cursor.fetchone()

    return dict(fila) if fila else None


# ---------------------------------------------------------------------------
# Función principal de autenticación
# ---------------------------------------------------------------------------

def autenticar(username: str, password: str, ip: str = "desconocida") -> dict:
    """
    Valida las credenciales de un usuario.

    Aplica, en orden:
      1. Validación básica de entrada.
      2. Límite de longitud de contraseña.
      3. Bloqueo por intentos fallidos.
      4. Verificación del hash.

    Returns:
        dict con la forma:
          {"ok": True,  "usuario": {id, username, rol}}
          {"ok": False, "error": "...", "bloqueado": bool}
    """
    username = (username or "").strip()

    # 1. Entrada vacía
    if not username or not password:
        return {"ok": False, "error": "Usuario y contraseña son obligatorios."}

    # 2. Contraseña demasiado larga (no la hasheamos siquiera)
    if len(password) > MAX_LARGO_PASSWORD:
        return {
            "ok": False,
            "error": f"La contraseña no puede superar {MAX_LARGO_PASSWORD} caracteres.",
        }

    # 3. ¿Está bloqueado por demasiados intentos?
    bloqueado, restante = esta_bloqueado(username, ip)
    if bloqueado:
        minutos = max(1, restante // 60)
        return {
            "ok": False,
            "bloqueado": True,
            "error": f"Demasiados intentos. Intenta de nuevo en ~{minutos} min.",
        }

    # 4. Verificar credenciales
    usuario = buscar_usuario(username)

    # Verificamos el hash aunque el usuario no exista para no revelar
    # (por tiempo de respuesta) si el username es válido o no.
    hash_guardado = usuario.get("password_hash") if usuario else None
    credenciales_ok = usuario is not None and verificar_password(password, hash_guardado)

    if not credenciales_ok:
        _registrar_fallo(username, ip)
        return {"ok": False, "error": "Usuario o contraseña incorrectos."}

    # Éxito: limpiamos intentos y devolvemos datos públicos del usuario.
    _limpiar_intentos(username, ip)
    return {
        "ok": True,
        "usuario": {
            "id": usuario["id"],
            "username": usuario["username"],
            "rol": usuario["rol"],
        },
    }
