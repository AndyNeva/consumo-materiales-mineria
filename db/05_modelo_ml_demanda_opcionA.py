#!/usr/bin/env python3
"""
OPCIÓN A – MODELO ML DE DEMANDA (BENCHMARK)
------------------------------------------
Este script entrena un modelo de Machine Learning para predecir
la demanda diaria de producción (m3) usando EXCLUSIVAMENTE la
tabla daily_demand.

Ubicación temporal:
- Se mantiene en /db para facilitar revisión por el equipo.
- Si se aprueba, se moverá a /ml o /models sin cambiar la lógica.

IMPORTANTE:
- NO modifica la base de datos.
- SOLO lee daily_demand.
"""

import os
import sqlite3
from datetime import timedelta
import pandas as pd

from sklearn.ensemble import GradientBoostingRegressor
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
# FEATURE ENGINEERING
# --------------------------------------------------
def preparar_features(df):
    df = df.copy()

    df['anio'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    df['dia'] = df['fecha'].dt.day
    df['dia_semana'] = df['fecha'].dt.dayofweek

    # Lags simples (capturan tendencia reciente)
    for lag in [1, 7, 14]:
        df[f'lag_{lag}'] = df['volume_m3'].shift(lag)

    # Eliminar filas iniciales con NaN por lags
    df = df.dropna().reset_index(drop=True)

    X = df.drop(columns=['fecha', 'volume_m3'])
    y = df['volume_m3']

    return X, y, df


# --------------------------------------------------
# ENTRENAMIENTO
# --------------------------------------------------
def entrenar_modelo(X, y):
    split_idx = int(len(X) * 0.8)

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = GradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)

    return model, X_test, y_test


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
def forecast_futuro(model, df, days=365):
    last_date = df['fecha'].max()
    future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=days)

    future = pd.DataFrame({'fecha': future_dates})
    future['anio'] = future['fecha'].dt.year
    future['mes'] = future['fecha'].dt.month
    future['dia'] = future['fecha'].dt.day
    future['dia_semana'] = future['fecha'].dt.dayofweek

    # Aproximación conservadora: último valor real
    last_value = df['volume_m3'].iloc[-1]
    future['lag_1'] = last_value
    future['lag_7'] = last_value
    future['lag_14'] = last_value

    preds = model.predict(future.drop(columns=['fecha']))
    future['pred_volume_m3'] = preds

    return future


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== OPCIÓN A | MODELO ML DE DEMANDA ===")

    df = cargar_daily_demand()
    if df.empty or len(df) < 30:
        print("No hay suficientes datos para entrenar el modelo.")
        return

    X, y, df_feat = preparar_features(df)
    model, X_test, y_test = entrenar_modelo(X, y)

    metrics = evaluar_modelo(model, X_test, y_test)

    print("\n--- Métricas del modelo ---")
    print(f"R2:   {metrics['R2']:.4f}")
    print(f"MAE:  {metrics['MAE']:.2f} m3")
    print(f"RMSE: {metrics['RMSE']:.2f} m3")

    future = forecast_futuro(model, df_feat, days=365)

    print("\n--- Pronóstico inicial (primeros 5 días) ---")
    print(future[['fecha', 'pred_volume_m3']].head())

    print("\nModelo ejecutado correctamente.")
    print("Este resultado se usará para comparar con la OPCIÓN B.")


if __name__ == "__main__":
    main()

