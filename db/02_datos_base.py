import sqlite3
import os

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

# --------------------------------------------------
# INSERCIÓN DE DATOS BASE
# --------------------------------------------------
def cargar_datos_base():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()
    print("✅ Datos base cargados.")

# --------------------------------------------------
# EJECUCIÓN DIRECTA
# --------------------------------------------------
if __name__ == "__main__":
    cargar_datos_base()
