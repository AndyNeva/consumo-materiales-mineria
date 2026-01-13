#!/usr/bin/env python3
"""
VERIFICADOR DE OUTLIERS POR PERCENTILES
--------------------------------------
Identifica los días de producción diaria
que quedan fuera de los percentiles P1 y P99.

Objetivo:
- Contar cuántos días son outliers
- Ver qué fechas y valores presentan producción extrema
- Decidir con evidencia si se limpian o se conservan
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

# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
def cargar_daily_demand():
    """
    Carga la demanda diaria desde SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT date AS fecha, volume_m3
        FROM daily_demand
        ORDER BY date
    """, conn)
    conn.close()

    df['fecha'] = pd.to_datetime(df['fecha'])
    return df


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== VERIFICACIÓN DE OUTLIERS (PERCENTILES) ===")

    # 1. Cargar datos
    df = cargar_daily_demand()

    if df.empty:
        print("No hay datos en daily_demand.")
        return

    y = df['volume_m3']

    # 2. Calcular percentiles
    p1 = np.percentile(y, 1)
    p99 = np.percentile(y, 99)

    # 3. Identificar outliers
    outliers = df[(y < p1) | (y > p99)]

    # 4. Resultados generales
    total = len(df)
    n_outliers = len(outliers)
    porcentaje = (n_outliers / total) * 100

    print(f"Límite inferior (P1): {p1:.2f} m³")
    print(f"Límite superior (P99): {p99:.2f} m³")
    print(f"Total de días analizados: {total}")
    print(f"Días fuera de rango: {n_outliers}")
    print(f"Porcentaje de outliers: {porcentaje:.2f}%")

    # 5. Mostrar fechas y valores outliers
    if n_outliers > 0:
        print("\n--- LISTADO DE DÍAS OUTLIERS (ordenados por volumen) ---")
        print(
            outliers[['fecha', 'volume_m3']]
            .sort_values('volume_m3', ascending=False)
            .to_string(index=False)
        )

        print("\n--- RESUMEN ESTADÍSTICO DE LOS OUTLIERS ---")
        print(outliers['volume_m3'].describe())

    else:
        print("\nNo se identificaron outliers según el criterio de percentiles.")


if __name__ == "__main__":
    main()
