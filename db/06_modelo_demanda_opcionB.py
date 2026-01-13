#!/usr/bin/env python3
"""
OPCIÓN B – MODELO SIMPLE Y EXPLICABLE DE DEMANDA
-----------------------------------------------
Modelo basado en:
- Demanda diaria agregada (daily_demand)
- Suavizado semanal
- Regresión lineal sobre el tiempo

Objetivo:
- Forecast diario defendible
- Comparación directa con la Opción A
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import timedelta

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from math import sqrt


# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")


# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
def cargar_daily_demand():
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
# PREPARACIÓN: AGREGACIÓN SEMANAL
# --------------------------------------------------
def preparar_serie_semanal(df):
    df = df.copy()
    df.set_index('fecha', inplace=True)

    # Producción semanal total
    weekly = df.resample('W').sum().reset_index()
    weekly['t'] = np.arange(len(weekly))  # tiempo como variable explicativa

    return weekly


# --------------------------------------------------
# ENTRENAMIENTO
# --------------------------------------------------
def entrenar_modelo(weekly):
    X = weekly[['t']]
    y = weekly['volume_m3']

    split = int(len(weekly) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = LinearRegression()
    model.fit(X_train, y_train)

    return model, X_test, y_test, weekly


# --------------------------------------------------
# EVALUACIÓN
# --------------------------------------------------
def evaluar_modelo(model, X_test, y_test):
    preds = model.predict(X_test)
    return {
        "R2": r2_score(y_test, preds),
        "MAE": mean_absolute_error(y_test, preds),
        "RMSE": sqrt(mean_squared_error(y_test, preds))
    }


# --------------------------------------------------
# FORECAST FUTURO
# --------------------------------------------------
def forecast_futuro(model, weekly, days=365):
    last_week = weekly.iloc[-1]
    last_date = last_week['fecha']

    future_weeks = int(np.ceil(days / 7))
    t_start = weekly['t'].max() + 1

    future_t = np.arange(t_start, t_start + future_weeks)
    future_volume_week = model.predict(future_t.reshape(-1, 1))

    # Reconstruir a diario (promedio diario semanal)
    records = []
    for i, vol in enumerate(future_volume_week):
        start = last_date + timedelta(days=7*i + 1)
        for d in range(7):
            records.append({
                "fecha": start + timedelta(days=d),
                "pred_volume_m3": max(vol / 7, 0)  # evitar negativos
            })

    future = pd.DataFrame(records)
    return future.head(days)


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== OPCIÓN B | MODELO SIMPLE Y EXPLICABLE ===")

    df = cargar_daily_demand()
    if df.empty or len(df) < 30:
        print("No hay suficientes datos.")
        return

    weekly = preparar_serie_semanal(df)
    model, X_test, y_test, weekly = entrenar_modelo(weekly)

    metrics = evaluar_modelo(model, X_test, y_test)

    print("\n--- Métricas del modelo ---")
    print(f"R2:   {metrics['R2']:.4f}")
    print(f"MAE:  {metrics['MAE']:.2f} m3/semana")
    print(f"RMSE: {metrics['RMSE']:.2f} m3/semana")

    future = forecast_futuro(model, weekly, days=365)

    print("\n--- Pronóstico inicial (primeros 5 días) ---")
    print(future.head())

    coef = model.coef_[0]
    print("\n--- Interpretación ---")
    print(f"Tendencia semanal aproximada: {coef:.2f} m3 por semana")

    print("\nModelo Opción B ejecutado correctamente.")


if __name__ == "__main__":
    main()
