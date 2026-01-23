import sqlite3
import os

# Configuración

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

def cargar_datos_base():
    """Carga usuarios y materiales iniciales en la BD"""
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    # Usuario administrador
    cursor.execute(
        "INSERT OR IGNORE INTO usuarios (username, rol) VALUES ('admin', 'Admin')"
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
