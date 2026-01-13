import sqlite3
import pandas as pd
import os

# Buscamos la base de datos en la misma carpeta
DB_PATH = os.path.join("db", "gestion_materiales.db")

if not os.path.exists(DB_PATH):
    print("❌ No encuentro la base de datos. ¿Ya ejecutaste la migración?")
else:
    print(f"📂 Conectando a: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    # Función para mostrar tablas bonitas
    def ver_tabla(nombre):
        print(f"\n--- 📊 VISTA PREVIA: {nombre.upper()} (Primeras 5 filas) ---")
        try:
            df = pd.read_sql_query(f"SELECT * FROM {nombre} LIMIT 5", conn)
            print(df.to_string(index=False)) # Imprime sin el índice numérico
            
            # Contamos el total
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {nombre}")
            total = cursor.fetchone()[0]
            print(f"✅ Total de registros: {total}")
        except Exception as e:
            print(f"⚠️ Error leyendo {nombre}: {e}")

    # Consultamos las tablas principales
    ver_tabla("usuarios")
    ver_tabla("despachos")
    ver_tabla("movimientos")
    ver_tabla("recetas")
    ver_tabla("materiales")
    ver_tabla("daily_demand")   

    conn.close()