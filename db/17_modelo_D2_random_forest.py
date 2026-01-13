#!/usr/bin/env python3
"""
MODELO D2 – RANDOM FOREST REGRESSOR
----------------------------------
Modelo no lineal basado en árboles
para predecir la demanda diaria.

Objetivo:
- Comparar contra promedio móvil
- Ver si un modelo más complejo
  realmente mejora los indicadores
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
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
    """
    Carga la demanda diaria limpia y
    genera variables temporales.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT date AS fecha, volume_m3
        FROM daily_demand_clean
        ORDER BY date
    """, conn)
    conn.close()

    df['fecha'] = pd.to_datetime(df['fecha'])

    # Variables temporales explicativas
    df['anio'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    df['dia'] = df['fecha'].dt.day
    df['dia_semana'] = df['fecha'].dt.dayofweek

    # Variable temporal continua
    df['t'] = (df['fecha'] - df['fecha'].min()).dt.days

    return df

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== MODELO D2 | RANDOM FOREST REGRESSOR ===")

    df = cargar_datos()

    # Variables explicativas
    features = ['anio', 'mes', 'dia', 'dia_semana', 't']
    X = df[features]
    y = df['volume_m3']

    # Split temporal 80/20
    split = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    # Modelo Random Forest
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )

    print("Entrenando modelo...")
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
    print("Random Forest captura relaciones no lineales,")
    print("pero no conoce los factores externos de la demanda.")

    print("\nModelo ejecutado correctamente.")

if __name__ == "__main__":
    main()
