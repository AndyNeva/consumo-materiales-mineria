import sqlite3
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

conexion = sqlite3.connect(DB_PATH)

df_recetas = pd.read_sql("""
    SELECT *
    FROM recetas
    ORDER BY codigo_diseno
""", conexion)

conexion.close()

print("Cantidad de recetas:", len(df_recetas))
print("\nPrimeras recetas:")
print(df_recetas.head())

print("\nResumen estadístico:")
print(df_recetas.describe())
