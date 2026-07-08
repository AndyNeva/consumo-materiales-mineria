import sqlite3
import pandas as pd
import os

# Buscamos la base de datos en la misma carpeta
DB_PATH = os.path.join("db", "gestion_materiales.db")

if not os.path.exists(DB_PATH):
    print("No encuentro la base de datos. ¿Ya ejecutaste la migración?")
else:
    print(f"[INFO] Conectando a: {DB_PATH}")
    conexion = sqlite3.connect(DB_PATH)

    # Función para mostrar tablas bonitas
    def ver_tabla(nombre):
        print(f"\n--- VISTA PREVIA: {nombre.upper()} (Primeras 5 filas) ---")
        try:
            df = pd.read_sql_query(f"SELECT * FROM {nombre} LIMIT 5", conexion)
            print(df.to_string(index=False)) # Imprime sin el índice numérico
            
            # Contamos el total
            cursor = conexion.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {nombre}")
            total = cursor.fetchone()[0]
            print(f"[OK] Total de registros: {total}")
        except Exception as e:
            print(f"Error leyendo {nombre}: {e}")

    # Consultamos las tablas principales
    ver_tabla("usuarios")
    ver_tabla("Produccion_Diaria")
    ver_tabla("Produccion_Insumos")
    ver_tabla("movimientos")
    ver_tabla("Disenos_Mezcla")
    ver_tabla("Receta_Detalle")
    ver_tabla("Insumos")
    ver_tabla("Zonas")
    ver_tabla("Centros_Costo")
    ver_tabla("Turnos")   

    conexion.close()