import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

con = sqlite3.connect(DB)
cur = con.cursor()

def ver_tabla(nombre):
    print("\n==============================")
    print("TABLA:", nombre)
    print("==============================")
    cur.execute(f"PRAGMA table_info({nombre})")
    rows = cur.fetchall()
    for cid, name, ctype, notnull, dflt, pk in rows:
        print(f"- {name} ({ctype})")

ver_tabla("despachos")
ver_tabla("recetas")

con.close()
