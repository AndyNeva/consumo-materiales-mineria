#!/usr/bin/env python3
"""
VERIFICADOR DE OUTLIERS POR IQR
------------------------------
Identifica días de producción diaria que se encuentran
fuera del rango intercuartílico (IQR).

Objetivo:
- Contar cuántos días son outliers
- Ver qué fechas y valores presentan producción extrema
- Decidir con evidencia si se limpian o se conservan
"""

import sqlite3
import pandas as pd
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
    print("=== VERIFICACIÓN DE OUTLIERS (IQR) ===")

    # 1. Cargar datos
    df = cargar_daily_demand()

    if df.empty:
        print("No hay datos en daily_demand.")
        return

    y = df['volume_m3']

    # 2. Calcular cuartiles
    Q1 = y.quantile(0.25)
    Q3 = y.quantile(0.75)
    IQR = Q3 - Q1

    lim_inf = Q1 - 1.5 * IQR
    lim_sup = Q3 + 1.5 * IQR

    # 3. Identificar outliers
    outliers = df[(y < lim_inf) | (y > lim_sup)]

    # 4. Resultados generales
    total = len(df)
    n_outliers = len(outliers)
    porcentaje = (n_outliers / total) * 100

    print(f"Q1 (25%): {Q1:.2f} m³")
    print(f"Q3 (75%): {Q3:.2f} m³")
    print(f"IQR:      {IQR:.2f}")
    print(f"Límite inferior: {lim_inf:.2f} m³")
    print(f"Límite superior: {lim_sup:.2f} m³")
    print(f"\nTotal de días: {total}")
    print(f"Días fuera de rango: {n_outliers}")
    print(f"Porcentaje de outliers: {porcentaje:.2f}%")

    # 5. Mostrar fechas y valores outlier
    if n_outliers > 0:
        print("\n--- DÍAS IDENTIFICADOS COMO OUTLIERS ---")
        print(outliers[['fecha', 'volume_m3']].sort_values('volume_m3', ascending=False).head(20))

        print("\n--- RESUMEN ESTADÍSTICO DE OUTLIERS ---")
        print(outliers['volume_m3'].describe())

    else:
        print("\nNo se identificaron outliers según el criterio IQR.")


if __name__ == "__main__":
    main()
