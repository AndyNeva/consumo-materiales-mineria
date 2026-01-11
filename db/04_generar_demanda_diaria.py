import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    INSERT OR REPLACE INTO daily_demand (date, volume_m3)
    SELECT date(fecha), SUM(volumen_m3)
    FROM despachos
    GROUP BY date(fecha)
""")

conn.commit()
conn.close()

print("✅ Demanda diaria generada correctamente.")
