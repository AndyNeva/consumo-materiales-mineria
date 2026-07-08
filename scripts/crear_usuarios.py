"""
Script para poblar la tabla 'usuarios' con datos iniciales hasheados.

Responsable: Juan Ruiz (@eljuandaruiz) — módulo de autenticación.

Qué hace:
  1. Se asegura de que la tabla 'usuarios' tenga la columna 'password_hash'
     (la añade con ALTER TABLE si falta; es idempotente y no toca el esquema
     base que mantiene otro módulo).
  2. Crea/actualiza un usuario por cada rol con su contraseña hasheada.

Cómo ejecutarlo (desde la raíz del proyecto):

    python scripts/crear_usuarios.py

Vuelve a ejecutarlo cuando quieras restablecer las contraseñas iniciales.
"""

from __future__ import annotations

import os
import sys

# Permite importar 'utils' y 'auth' al correr el script directamente.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import conectar  # noqa: E402
from auth.login import hashear_password  # noqa: E402

# Usuarios iniciales: (username, password, rol).
# ⚠️ Cambia estas contraseñas en un entorno real. Sirven para arrancar/demostrar.
USUARIOS_INICIALES = [
    ("admin", "admin123", "Admin"),
    ("operador", "operador123", "Operador"),
    ("visor", "visor123", "Visualizador"),
]


def asegurar_columna_password(conexion) -> None:
    """Añade la columna password_hash a 'usuarios' si todavía no existe."""
    cursor = conexion.cursor()
    cursor.execute("PRAGMA table_info(usuarios)")
    columnas = [fila["name"] for fila in cursor.fetchall()]

    if "password_hash" not in columnas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN password_hash TEXT")
        print("[+] Columna 'password_hash' anadida a la tabla usuarios.")
    else:
        print("[i] La columna 'password_hash' ya existia.")


def crear_usuarios() -> None:
    """Inserta o actualiza los usuarios iniciales con contraseñas hasheadas."""
    with conectar() as conexion:
        asegurar_columna_password(conexion)
        cursor = conexion.cursor()

        for username, password, rol in USUARIOS_INICIALES:
            password_hash = hashear_password(password)

            # UPSERT con consulta parametrizada (sin concatenar strings).
            # Si el username ya existe, actualiza rol y hash.
            cursor.execute(
                """
                INSERT INTO usuarios (username, rol, password_hash)
                VALUES (?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    rol = excluded.rol,
                    password_hash = excluded.password_hash
                """,
                (username, rol, password_hash),
            )
            print(f"[OK] Usuario '{username}' listo  (rol: {rol})")

        conexion.commit()

    print("\nUsuarios iniciales creados/actualizados correctamente.")
    print("   Credenciales de arranque:")
    for username, password, rol in USUARIOS_INICIALES:
        print(f"     - {username} / {password}   ({rol})")


if __name__ == "__main__":
    crear_usuarios()
