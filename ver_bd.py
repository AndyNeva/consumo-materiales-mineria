import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

print("DB =", DB)

con = sqlite3.connect(DB)
cur = con.cursor()

# 1) Tablas
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("TABLAS =", cur.fetchall())

# 2) Conteo de despachos
cur.execute("SELECT COUNT(*) FROM despachos")
print("TOTAL despachos =", cur.fetchone()[0])

# 3) Rango de fechas
cur.execute("SELECT MIN(fecha), MAX(fecha) FROM despachos")
print("RANGO fechas (MIN, MAX) =", cur.fetchone())

con.close()
