#!/usr/bin/env python3
"""
CREAR COPIA DE DAILY_DEMAND
--------------------------
Crea una tabla daily_demand_clean como copia exacta
de daily_demand para pruebas de limpieza.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

def main():
    print("=== CREANDO COPIA DE DAILY_DEMAND ===")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Eliminar tabla si ya existe
    cursor.execute("DROP TABLE IF EXISTS daily_demand_clean")

    # 2. Crear copia exacta
    cursor.execute("""
        CREATE TABLE daily_demand_clean AS
        SELECT *
        FROM daily_demand
    """)

    # 3. Verificar
    cursor.execute("SELECT COUNT(*) FROM daily_demand_clean")
    total = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    print(f"Tabla daily_demand_clean creada correctamente.")
    print(f"Total de registros copiados: {total}")

if __name__ == "__main__":
    main()
