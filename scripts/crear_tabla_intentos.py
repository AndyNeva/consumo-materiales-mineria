"""
crea la tabla 'intentos_login' en la bd actual sin recrear el resto.

esta tabla persiste los intentos fallidos de login y el bloqueo de 24h
contra ataques de fuerza bruta. es idempotente: si la tabla ya existe no
hace nada, asi q se puede correr varias veces sin riesgo.

como ejecutarlo (desde la raiz del proyecto):

    python scripts/crear_tabla_intentos.py
"""

from __future__ import annotations

import os
import sys

# permite importar 'utils' al correr el script directamente.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import conectar  # noqa: E402


def crear_tabla_intentos() -> None:
    """crea la tabla intentos_login si todavia no existe."""
    with conectar() as conexion:
        cursor = conexion.cursor()
        # clave = usuario+ip; bloqueado_hasta es un timestamp unix.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS intentos_login (
                clave TEXT PRIMARY KEY,
                intentos INTEGER NOT NULL DEFAULT 0,
                bloqueado_hasta REAL NOT NULL DEFAULT 0
            )
            """
        )
        conexion.commit()
    print("[OK] tabla 'intentos_login' lista (bloqueo de fuerza bruta en bd).")


if __name__ == "__main__":
    crear_tabla_intentos()
