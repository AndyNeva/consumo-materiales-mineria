"""
Lógica de autenticación del sistema.

Aquí vive todo lo relacionado con verificar credenciales:
- Hash y verificación de contraseñas con Werkzeug (viene con Flask).
- Límite de longitud de contraseña (anti abuso de recursos al hashear).
- Límite de intentos fallidos con bloqueo temporal por usuario/IP.
- Consultas SIEMPRE parametrizadas (sin concatenar strings) -> anti SQL injection.

"""

from __future__ import annotations

import time
from werkzeug.security import generate_password_hash, check_password_hash

from utils.db import conectar
from utils.logging_seguridad import logger_seguridad

# ---------------------------------------------------------------------------
# Configuración del módulo
# ---------------------------------------------------------------------------

# Longitud máxima de contraseña aceptada antes de hashear.
# Werkzeug no tiene el límite de 72 bytes de bcrypt, pero igual rechazamos
# entradas absurdamente largas para no gastar CPU hasheando textos enormes.
MAX_LARGO_PASSWORD = 128

# control de intentos fallidos de login.
MAX_INTENTOS = 5                  # intentos permitidos antes de bloquear
# bloqueo minimo de 24 horas ante fuerza bruta. asi un atacante no puede
# seguir probando claves el mismo dia tras pasarse del limite de intentos.
BLOQUEO_SEGUNDOS = 24 * 60 * 60   # 24 horas de bloqueo

# Roles válidos del sistema (debe coincidir con auth/roles.py).
ROLES_VALIDOS = ("Admin", "Operador", "Visualizador")

# los intentos fallidos se persisten en la tabla 'intentos_login' de la bd
# (no en memoria) para q el bloqueo aguante reinicios del servidor. asi un
# ataque de fuerza bruta no se reinicia cuando se reinicia el proceso flask.


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
    indica si la combinacion usuario/ip esta bloqueada.

    lee el estado desde la tabla 'intentos_login' (consulta parametrizada).

    Returns:
        (bloqueado, segundos_restantes)
    """
    clave = _clave_intentos(username, ip)
    with conectar() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT bloqueado_hasta FROM intentos_login WHERE clave = ?",
            (clave,),
        )
        fila = cursor.fetchone()

    if not fila:
        return False, 0

    # restante = cuanto falta para q expire el bloqueo, en segundos.
    restante = int(fila["bloqueado_hasta"] - time.time())
    if restante > 0:
        return True, restante

    return False, 0


def _registrar_fallo(username: str, ip: str) -> tuple[int, bool]:
    """
    suma un intento fallido en la bd y activa el bloqueo si se pasa del limite.

    usa upsert parametrizado: si la clave ya existe suma 1 al contador, si no
    crea la fila. cuando los intentos llegan a MAX_INTENTOS se fija
    bloqueado_hasta = ahora + BLOQUEO_SEGUNDOS (24 horas).

    Returns:
        (intentos_acumulados, se_acaba_de_bloquear)
    """
    clave = _clave_intentos(username, ip)
    bloqueo = time.time() + BLOQUEO_SEGUNDOS

    with conectar() as conexion:
        cursor = conexion.cursor()
        # primero insertamos o sumamos el intento.
        cursor.execute(
            """
            INSERT INTO intentos_login (clave, intentos, bloqueado_hasta)
            VALUES (?, 1, 0)
            ON CONFLICT(clave) DO UPDATE SET
                intentos = intentos + 1
            """,
            (clave,),
        )
        # si con este intento se alcanza el limite, activamos el bloqueo de 24h.
        cursor.execute(
            """
            UPDATE intentos_login
            SET bloqueado_hasta = ?
            WHERE clave = ? AND intentos >= ?
            """,
            (bloqueo, clave, MAX_INTENTOS),
        )
        conexion.commit()

        cursor.execute(
            "SELECT intentos, bloqueado_hasta FROM intentos_login WHERE clave = ?",
            (clave,),
        )
        fila = cursor.fetchone()

    intentos = int(fila["intentos"]) if fila else 0
    bloqueado_ahora = bool(fila and fila["bloqueado_hasta"] > time.time())
    return intentos, bloqueado_ahora


def mensaje_bloqueo(restante: int) -> str:
    """mensaje unico de bloqueo, expresado en horas (el bloqueo es de 24h)."""
    horas = max(1, -(-restante // 3600))  # redondeo hacia arriba
    return (
        "Cuenta bloqueada por 24 horas tras "
        f"{MAX_INTENTOS} intentos fallidos. "
        f"Inténtalo de nuevo en ~{horas} h."
    )


def estado_bloqueo_ip(ip: str) -> tuple[bool, int]:
    """
    dice si hay algun bloqueo activo desde esta ip, sin saber el usuario.

    la usa el login al cargar la pagina: si el navegador recarga (F5) el
    formulario se dibuja limpio y el usuario cree que el contador se reinicio.
    consultando esto al arrancar la pagina el bloqueo se pinta de una.

    como la clave es 'usuario@ip', aqui buscamos el bloqueo mas largo que siga
    vigente para esa ip (LIKE parametrizado sobre el sufijo).

    Returns:
        (bloqueado, segundos_restantes)
    """
    sufijo = f"%@{ip or 'desconocida'}"
    ahora = time.time()

    with conectar() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT MAX(bloqueado_hasta) AS hasta
            FROM intentos_login
            WHERE clave LIKE ? AND bloqueado_hasta > ?
            """,
            (sufijo, ahora),
        )
        fila = cursor.fetchone()

    if not fila or fila["hasta"] is None:
        return False, 0

    restante = int(fila["hasta"] - ahora)
    return (True, restante) if restante > 0 else (False, 0)


def _limpiar_intentos(username: str, ip: str) -> None:
    """borra el registro de intentos de la bd tras un login exitoso."""
    clave = _clave_intentos(username, ip)
    with conectar() as conexion:
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM intentos_login WHERE clave = ?", (clave,))
        conexion.commit()


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

    # 2. Contraseña demasiado larga
    if len(password) > MAX_LARGO_PASSWORD:
        logger_seguridad.warning(
            "Intento de login con password excesivamente largo | usuario=%s ip=%s",
            username, ip
        )
        return {
            "ok": False,
            "error": f"La contraseña no puede superar {MAX_LARGO_PASSWORD} caracteres.",
        }

    # 3. ¿Está bloqueado por demasiados intentos?
    bloqueado, restante = esta_bloqueado(username, ip)
    if bloqueado:
        logger_seguridad.warning(
            "Intento de login en cuenta bloqueada | usuario=%s ip=%s restante=%ss",
            username, ip, restante
        )
        return {
            "ok": False,
            "bloqueado": True,
            "error": mensaje_bloqueo(restante),
        }

    # 4. Verificar credenciales
    usuario = buscar_usuario(username)
    hash_guardado = usuario.get("password_hash") if usuario else None
    credenciales_ok = usuario is not None and verificar_password(password, hash_guardado)

    if not credenciales_ok:
        intentos, bloqueado_ahora = _registrar_fallo(username, ip)
        logger_seguridad.warning(
            "Login fallido | usuario=%s ip=%s intentos=%s", username, ip, intentos
        )

        # si este mismo intento fue el que alcanzo el limite, avisamos del
        # bloqueo aqui mismo en vez de esperar al siguiente intento.
        if bloqueado_ahora:
            logger_seguridad.warning(
                "Cuenta bloqueada 24h por fuerza bruta | usuario=%s ip=%s", username, ip
            )
            return {
                "ok": False,
                "bloqueado": True,
                "error": mensaje_bloqueo(BLOQUEO_SEGUNDOS),
            }

        restantes = max(0, MAX_INTENTOS - intentos)
        return {
            "ok": False,
            "error": (
                "Usuario o contraseña incorrectos. "
                f"Te quedan {restantes} intento(s) antes del bloqueo de 24 horas."
            ),
        }

    # Éxito
    _limpiar_intentos(username, ip)
    logger_seguridad.info(
        "Login exitoso | usuario=%s rol=%s ip=%s",
        usuario["username"], usuario["rol"], ip
    )
    return {
        "ok": True,
        "usuario": {
            "id": usuario["id"],
            "username": usuario["username"],
            "rol": usuario["rol"],
        },
    }
