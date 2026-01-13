#!/usr/bin/env python3
"""
LIMPIEZA POR PERCENTILES (P1–P99)
--------------------------------
Elimina de daily_demand_clean los días
fuera de los percentiles definidos,
sin alterar la tabla original.
"""

import sqlite3
import pandas as pd
import numpy as np
import os

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

def main():
    print("=== LIMPIEZA DE DAILY_DEMAND_CLEAN (PERCENTILES) ===")

    conn = sqlite3.connect(DB_PATH)

    # 1. Cargar datos
    df = pd.read_sql("""
        SELECT date, volume_m3
        FROM daily_demand_clean
        ORDER BY date
    """, conn)

    total_inicial = len(df)

    y = df['volume_m3']

    # 2. Calcular percentiles
    p1 = np.percentile(y, 1)
    p99 = np.percentile(y, 99)

    print(f"Límite inferior (P1): {p1:.2f} m³")
    print(f"Límite superior (P99): {p99:.2f} m³")

    # 3. Filtrar datos válidos
    df_filtrado = df[(y >= p1) & (y <= p99)]

    eliminados = total_inicial - len(df_filtrado)

    # 4. Reemplazar contenido de la tabla clean
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_demand_clean")

    # IMPORTANTE: columnas coinciden exactamente con la tabla SQL
    df_filtrado.to_sql(
        "daily_demand_clean",
        conn,
        if_exists="append",
        index=False
    )

    conn.commit()
    conn.close()

    print(f"Registros iniciales: {total_inicial}")
    print(f"Registros eliminados: {eliminados}")
    print(f"Registros finales: {len(df_filtrado)}")

if __name__ == "__main__":
    main()
