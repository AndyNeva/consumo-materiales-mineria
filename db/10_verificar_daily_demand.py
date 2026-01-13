import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Contar registros
cursor.execute("SELECT COUNT(*) FROM daily_demand")
total = cursor.fetchone()[0]

# Ver rango de fechas
cursor.execute("SELECT MIN(date), MAX(date) FROM daily_demand")
min_date, max_date = cursor.fetchone()

conn.close()

print("=== VERIFICACIÓN DE DAILY_DEMAND ===")
print(f"Total de registros (días): {total}")
print(f"Fecha inicial: {min_date}")
print(f"Fecha final:   {max_date}")

