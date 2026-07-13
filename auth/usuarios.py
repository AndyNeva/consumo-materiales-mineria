"""
Funciones para gestion de usuarios del sistema.

Incluye validaciones para crear usuarios desde la pantalla de administracion:
- usuario obligatorio y no repetido;
- contrasena con letras, numeros y simbolos;
- cedula con formato valido (checksum + bloqueo de patrones triviales);
- rol dentro de los roles permitidos.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from auth.login import MAX_LARGO_PASSWORD, hashear_password
from auth.roles import ROLES_VALIDOS
from utils.db import conectar
from utils.validaciones import validar_cedula


MAX_LARGO_USERNAME = 50


def _abrir_conexion(ruta_bd: str | None = None):
    """Abre la conexion usando la ruta por defecto o una ruta recibida."""
    return conectar() if ruta_bd is None else conectar(ruta_bd)


def asegurar_tabla_usuarios(conexion: sqlite3.Connection) -> None:
    """Crea o ajusta la tabla usuarios para soportar contrasenas hasheadas y cedula."""
    cursor = conexion.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            rol TEXT,
            password_hash TEXT
        )
        """
    )

    cursor.execute("PRAGMA table_info(usuarios)")
    columnas = [fila["name"] for fila in cursor.fetchall()]

    if "password_hash" not in columnas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN password_hash TEXT")

    if "cedula" not in columnas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN cedula TEXT")


def validar_password(password: str) -> list[str]:
    """Devuelve una lista de errores de validacion de contrasena."""
    errores: list[str] = []
    password = password or ""

    if not password:
        errores.append("La contraseña es obligatoria.")
        return errores

    if len(password) > MAX_LARGO_PASSWORD:
        errores.append(f"La contraseña no puede superar {MAX_LARGO_PASSWORD} caracteres.")

    if not any(caracter.isalpha() for caracter in password):
        errores.append("La contraseña debe contener al menos una letra.")

    if not any(caracter.isdigit() for caracter in password):
        errores.append("La contraseña debe contener al menos un número.")

    if not any((not caracter.isalnum()) and (not caracter.isspace()) for caracter in password):
        errores.append("La contraseña debe contener al menos un símbolo.")

    return errores


def validar_datos_usuario(
    username: str, password: str, rol: str, cedula: str = ""
) -> tuple[str, str, str, str, list[str]]:
    """Normaliza y valida los campos principales de usuario."""
    username = (username or "").strip()
    rol = (rol or "").strip()
    cedula = (cedula or "").strip()
    errores: list[str] = []

    if not username:
        errores.append("El nombre de usuario es obligatorio.")
    elif len(username) > MAX_LARGO_USERNAME:
        errores.append(f"El nombre de usuario no puede superar {MAX_LARGO_USERNAME} caracteres.")

    if rol not in ROLES_VALIDOS:
        errores.append("El rol seleccionado no es válido.")

    if not cedula:
        errores.append("La cédula es obligatoria.")
    elif not validar_cedula(cedula):
        errores.append("La cédula ingresada no es válida.")

    errores.extend(validar_password(password))

    return username, password or "", rol, cedula, errores


def usuario_existe(username: str, ruta_bd: str | None = None) -> bool:
    """Valida duplicados sin distinguir mayusculas/minusculas."""
    with _abrir_conexion(ruta_bd) as conexion:
        asegurar_tabla_usuarios(conexion)
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(username) = LOWER(?) LIMIT 1", (username,))
        return cursor.fetchone() is not None


def cedula_existe(cedula: str, ruta_bd: str | None = None) -> bool:
    """Valida que la cedula no este ya registrada por otro usuario."""
    cedula = (cedula or "").strip()
    if not cedula:
        return False
    with _abrir_conexion(ruta_bd) as conexion:
        asegurar_tabla_usuarios(conexion)
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE cedula = ? LIMIT 1", (cedula,))
        return cursor.fetchone() is not None


def listar_usuarios(ruta_bd: str | None = None) -> list[dict[str, Any]]:
    """Lista usuarios sin exponer el hash de la contrasena."""
    with _abrir_conexion(ruta_bd) as conexion:
        asegurar_tabla_usuarios(conexion)
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT id, username, rol, cedula
            FROM usuarios
            ORDER BY LOWER(username)
            """
        )
        return [dict(fila) for fila in cursor.fetchall()]


def crear_usuario(
    username: str, password: str, rol: str, cedula: str = "", ruta_bd: str | None = None
) -> dict[str, Any]:
    """Crea un usuario nuevo con password hasheada y validacion de duplicados."""
    username, password, rol, cedula, errores = validar_datos_usuario(username, password, rol, cedula)
    if errores:
        return {"ok": False, "error": " ".join(errores), "status": 400}

    with _abrir_conexion(ruta_bd) as conexion:
        asegurar_tabla_usuarios(conexion)
        cursor = conexion.cursor()

        cursor.execute("SELECT id FROM usuarios WHERE LOWER(username) = LOWER(?) LIMIT 1", (username,))
        if cursor.fetchone():
            return {"ok": False, "error": "Ya existe un usuario con ese nombre.", "status": 409}

        cursor.execute("SELECT id FROM usuarios WHERE cedula = ? LIMIT 1", (cedula,))
        if cursor.fetchone():
            return {"ok": False, "error": "Ya existe un usuario registrado con esa cédula.", "status": 409}

        try:
            password_hash = hashear_password(password)
            cursor.execute(
                "INSERT INTO usuarios (username, rol, password_hash, cedula) VALUES (?, ?, ?, ?)",
                (username, rol, password_hash, cedula),
            )
            conexion.commit()
        except sqlite3.IntegrityError as error:
            mensaje = str(error).lower()
            if "cedula" in mensaje:
                return {"ok": False, "error": "Ya existe un usuario registrado con esa cédula.", "status": 409}
            return {"ok": False, "error": "Ya existe un usuario con ese nombre.", "status": 409}

        return {
            "ok": True,
            "usuario": {
                "id": cursor.lastrowid,
                "username": username,
                "rol": rol,
                "cedula": cedula,
            },
            "status": 201,
        }