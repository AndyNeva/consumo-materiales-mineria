import sqlite3
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

conexion = sqlite3.connect(DB_PATH)

# Fetch all recipe details
df_details = pd.read_sql("""
    SELECT 
        m.diseno_mezcla AS codigo_diseno,
        i.nombre_insumo,
        rd.cantidad_requerida
    FROM Receta_Detalle rd
    JOIN Disenos_Mezcla m ON rd.diseno_mezcla = m.diseno_mezcla
    JOIN Insumos i ON rd.id_insumo = i.id_insumo
""", conexion)

conexion.close()

if df_details.empty:
    print("No hay recetas registradas.")
else:
    # Pivot the table to show it flat
    df_recetas = df_details.pivot(index='codigo_diseno', columns='nombre_insumo', values='cantidad_requerida').fillna(0.0).reset_index()

    print("Cantidad de recetas:", len(df_recetas))
    print("\nPrimeras recetas:")
    print(df_recetas.head())

    print("\nResumen estadístico:")
    print(df_recetas.describe())
