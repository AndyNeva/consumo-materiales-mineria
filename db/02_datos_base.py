import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth.login import hashear_password

# Configuración

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

def cargar_datos_base():
    """Carga usuarios y materiales iniciales en la BD"""
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    cursor.execute("PRAGMA table_info(usuarios)")
    columnas_usuarios = [fila[1] for fila in cursor.fetchall()]
    if "password_hash" not in columnas_usuarios:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN password_hash TEXT")

    # Usuario administrador con contrasena hasheada.
    cursor.execute(
        """
        INSERT INTO usuarios (username, rol, password_hash)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            rol = excluded.rol,
            password_hash = COALESCE(usuarios.password_hash, excluded.password_hash)
        """,
        ("admin", "Admin", hashear_password("Admin123!")),
    )

    # Materiales base
    cursor.execute(
        "INSERT OR IGNORE INTO materiales (id, nombre, unidad) VALUES "
        "(1, 'Cemento', 'Kg'),"
        "(2, 'Arena', 'Kg'),"
        "(3, 'Grava', 'Kg')"
    )

    conexion.commit()
    conexion.close()
    print("Datos base cargados.")


if __name__ == "__main__":
    cargar_datos_base()
