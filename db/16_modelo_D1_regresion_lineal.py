#!/usr/bin/env python3
"""
MODELO D1 – REGRESIÓN LINEAL CON TENDENCIA
-----------------------------------------
Modelo explicable basado únicamente en el
paso del tiempo como variable independiente.

Objetivo:
- Servir como modelo de referencia simple
- Comparar contra el promedio móvil
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from math import sqrt

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

# --------------------------------------------------
# CARGA DE DATOS LIMPIOS
# --------------------------------------------------
def cargar_datos():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT date AS fecha, volume_m3
        FROM daily_demand_clean
        ORDER BY date
    """, conn)
    conn.close()

    df['fecha'] = pd.to_datetime(df['fecha'])

    # Variable temporal numérica (días desde inicio)
    df['t'] = (df['fecha'] - df['fecha'].min()).dt.days

    return df

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== MODELO D1 | REGRESIÓN LINEAL ===")

    df = cargar_datos()

    # Split temporal 80/20
    split = int(len(df) * 0.8)

    X_train = df[['t']].iloc[:split]
    y_train = df['volume_m3'].iloc[:split]

    X_test = df[['t']].iloc[split:]
    y_test = df['volume_m3'].iloc[split:]

    # Entrenamiento
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Predicción
    y_pred = model.predict(X_test)

    # Métricas
    mae = mean_absolute_error(y_test, y_pred)
    rmse = sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print("\n--- Métricas del modelo ---")
    print(f"MAE:  {mae:.2f} m³")
    print(f"RMSE: {rmse:.2f} m³")
    print(f"R2:   {r2:.4f}")

    print("\n--- Interpretación ---")
    print("El modelo asume una tendencia lineal en el tiempo.")
    print("No captura picos ni variabilidad diaria.")

    print("\nModelo ejecutado correctamente.")

if __name__ == "__main__":
    main()
