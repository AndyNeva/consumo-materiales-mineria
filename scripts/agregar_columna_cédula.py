"""
Añade la columna 'cedula' a la tabla 'usuarios' y permite actualizar
la cedula de los usuarios existentes que aún no la tengan.

Es idempotente: si la columna ya existe no la vuelve a crear, y si un
usuario ya tiene cedula no te la vuelve a pedir. Se puede correr varias
veces sin riesgo.

Como usarlo (desde la raíz del proyecto):

    python scripts/agregar_columna_cedula.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import conectar  # noqa: E402
from utils.validaciones import validar_cedula  # noqa: E402


def asegurar_columna_cedula(conexion) -> None:
    """Añade la columna cedula a usuarios si todavía no existe."""
    cursor = conexion.cursor()
    cursor.execute("PRAGMA table_info(usuarios)")
    columnas = [fila["name"] for fila in cursor.fetchall()]

    if "cedula" not in columnas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN cedula TEXT")
        conexion.commit()
        print("[OK] Columna 'cedula' añadida a la tabla usuarios.")
    else:
        print("[i] La columna 'cedula' ya existía.")


def pedir_cedula_valida(username: str) -> str | None:
    """
    Pide la cedula por consola hasta recibir una válida o que el
    usuario decida saltarla escribiendo 'skip'.
    """
    while True:
        entrada = input(
            f"  Cédula para '{username}' (10 dígitos, 'skip' para omitir): "
        ).strip()

        if entrada.lower() == "skip":
            return None

        if validar_cedula(entrada):
            return entrada

        print("  [!] Cédula inválida (formato, patrón trivial o checksum). Intenta de nuevo.")


def actualizar_usuarios_sin_cedula() -> None:
    """Recorre usuarios sin cedula y la pide interactivamente."""
    with conectar() as conexion:
        asegurar_columna_cedula(conexion)

        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT id, username FROM usuarios
            WHERE cedula IS NULL OR TRIM(cedula) = ''
            ORDER BY LOWER(username)
            """
        )
        pendientes = cursor.fetchall()

        if not pendientes:
            print("[i] Todos los usuarios ya tienen cédula registrada.")
            return

        print(f"\nUsuarios sin cédula: {len(pendientes)}")
        actualizados = 0
        omitidos = 0

        for fila in pendientes:
            cedula = pedir_cedula_valida(fila["username"])
            if cedula is None:
                omitidos += 1
                continue

            cursor.execute(
                "UPDATE usuarios SET cedula = ? WHERE id = ?",
                (cedula, fila["id"]),
            )
            print(f"  [OK] '{fila['username']}' actualizado con cédula {cedula}.")
            actualizados += 1

        conexion.commit()

    print(f"\nResumen: {actualizados} actualizados, {omitidos} omitidos.")


if __name__ == "__main__":
    actualizar_usuarios_sin_cedula()