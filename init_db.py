import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Tabla minima para que funcione:
# - 'fecha' obligatoria (la usan las estructuras de busqueda)
# - 'material' y 'cantidad' por el comentario de /api/agregar
cur.execute("""
CREATE TABLE IF NOT EXISTS despachos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    material TEXT NOT NULL,
    cantidad REAL NOT NULL
)
""")

# Datos de prueba (opcional pero recomendado para ver algo en el dashboard)
cur.execute("SELECT COUNT(*) FROM despachos")
count = cur.fetchone()[0]

if count == 0:
    cur.executemany(
        "INSERT INTO despachos (fecha, material, cantidad) VALUES (?, ?, ?)",
        [
            ("2025-11-15", "ARENA", 12.5),
            ("2025-11-15", "GRAVA", 18.0),
            ("2025-11-16", "ARENA", 9.75),
        ],
    )

conn.commit()
conn.close()

print("OK: Tabla 'despachos' creada en:", DB_PATH)
