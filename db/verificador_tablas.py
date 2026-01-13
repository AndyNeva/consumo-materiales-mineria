print("🚀 Script iniciado")

import sqlite3
import os

# Como estamos en la carpeta db, la base está aquí mismo
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gestion_materiales.db")

print("Ruta DB:", DB_PATH)
print("¿Existe DB?:", os.path.exists(DB_PATH))

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table';
""")

tablas = cursor.fetchall()

print("Tablas en la base de datos:")
for t in tablas:
    print("-", t[0])

conn.close()
print("✅ Script finalizado")