import os
import sqlite3

db = os.path.join(os.path.dirname(__file__), "db", "gestion_materiales.db")
print("DB =", db)

con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tablas = cur.fetchall()
print("TABLAS =", tablas)

# si existe despachos, contamos registros
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='despachos'")
existe = cur.fetchone()

if existe:
    cur.execute("SELECT COUNT(*) FROM despachos")
    print("REGISTROS despachos =", cur.fetchone()[0])
else:
    print("NO EXISTE la tabla 'despachos'")

con.close()
