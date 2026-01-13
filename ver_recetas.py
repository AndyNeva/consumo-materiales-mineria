import sqlite3

DB = r"D:\Proyecto\proyecto-consumo-materiales\db\gestion_materiales.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT id, codigo_diseno FROM recetas ORDER BY codigo_diseno LIMIT 50")
rows = cur.fetchall()

print("Primeras recetas:")
for r in rows:
    print(r)

# buscar H-25
cur.execute("SELECT * FROM recetas WHERE codigo_diseno = ?", ("H-25",))
r = cur.fetchone()
print("\nH-25 existe?:", "SI" if r else "NO")

conn.close()

cur.execute("SELECT DISTINCT codigo_diseno FROM recetas ORDER BY codigo_diseno")
rows = cur.fetchall()