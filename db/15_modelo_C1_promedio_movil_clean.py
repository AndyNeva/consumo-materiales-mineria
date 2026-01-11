#!/usr/bin/env python3
"""
MODELO C1 – PROMEDIO MÓVIL (DATOS LIMPIOS)
-----------------------------------------
Evalúa el modelo de promedio móvil usando
la tabla daily_demand_clean (sin outliers).

Objetivo:
- Comparar métricas vs datos originales
- Medir impacto real de la limpieza
"""

import os
import sqlite3
import pandas as pd
from math import sqrt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

# Ventanas a evaluar (las mismas que antes)
VENTANAS = [5, 7, 10, 14, 21, 28, 45, 60, 90, 120, 180, 270]

# --------------------------------------------------
# CARGA DE DATOS LIMPIOS
# --------------------------------------------------
def cargar_daily_demand_clean():
    """
    Carga la demanda diaria limpia desde SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT date AS fecha, volume_m3
        FROM daily_demand_clean
        ORDER BY date
    """, conn)
    conn.close()

    df['fecha'] = pd.to_datetime(df['fecha'])
    return df

# --------------------------------------------------
# EVALUACIÓN PROMEDIO MÓVIL
# --------------------------------------------------
def evaluar_promedio_movil(df, ventana):
    """
    Evalúa el modelo de promedio móvil
    usando split temporal 80/20.
    """
    df = df.copy()

    # Predicción = promedio móvil histórico
    df['pred'] = df['volume_m3'].rolling(window=ventana).mean()

    # Eliminar días sin predicción
    df = df.dropna().reset_index(drop=True)

    # División temporal (80% datos antiguos, 20% recientes)
    split = int(len(df) * 0.8)

    y_true = df['volume_m3'].iloc[split:]
    y_pred = df['pred'].iloc[split:]

    mae = mean_absolute_error(y_true, y_pred)
    rmse = sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    return {
        "Ventana_dias": ventana,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    }

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== MODELO C1 | PROMEDIO MÓVIL (DATOS LIMPIOS) ===")

    df = cargar_daily_demand_clean()

    if df.empty:
        print("No hay datos en daily_demand_clean.")
        return

    resultados = []

    for v in VENTANAS:
        res = evaluar_promedio_movil(df, v)
        resultados.append(res)

    resultados_df = pd.DataFrame(resultados).sort_values("MAE")

    print("\n--- Resultados comparativos (ordenados por MAE) ---")
    print(resultados_df)

    mejor = resultados_df.iloc[0]

    print("\n--- Mejor ventana (datos limpios) ---")
    print(mejor)

    print("\nModelo ejecutado correctamente.")

if __name__ == "__main__":
    main()
