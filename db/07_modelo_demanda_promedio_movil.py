#!/usr/bin/env python3
"""
MODELO C1 – PROMEDIO MÓVIL (BASELINE)
------------------------------------
Este script evalúa modelos de promedio móvil
sobre la tabla daily_demand para distintas
ventanas de tiempo.

Objetivo:
- Establecer un baseline sólido
- Comparar múltiples tamaños de ventana
- Determinar qué horizonte temporal representa
  mejor la demanda real para planificación
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

# Ventanas móviles a evaluar (en días)
# Cubren corto, mediano y largo plazo
VENTANAS = [
    5, 7, 10,
    14, 21, 28,
    45, 60, 90,
    120, 180, 270
]

# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
def cargar_daily_demand():
    """
    Carga la demanda diaria desde SQLite
    y la ordena cronológicamente.
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
# EVALUACIÓN DE PROMEDIO MÓVIL
# --------------------------------------------------
def evaluar_promedio_movil(df, ventana):
    """
    Evalúa un modelo de promedio móvil para una
    ventana específica usando validación temporal.

    Metodología:
    - Se calcula el promedio móvil usando SOLO
      valores pasados.
    - Se utiliza una división 80/20 preservando
      el orden cronológico:
        * 80% inicial → referencia histórica
        * 20% final   → validación (datos recientes)
    """

    df = df.copy()

    # Predicción = promedio móvil de los 'ventana' días anteriores
    df['pred'] = df['volume_m3'].rolling(window=ventana).mean()

    # Eliminamos los primeros registros que no tienen
    # suficiente historia para calcular el promedio
    df = df.dropna().reset_index(drop=True)

    # --------------------------------------------------
    # DIVISIÓN TEMPORAL 80/20 (ENTRENAMIENTO / PRUEBA)
    # --------------------------------------------------
    # Importante:
    # NO se mezclan los datos, ya que es una serie temporal.
    # El pasado predice el futuro, nunca al revés.
    split = int(len(df) * 0.8)

    # Datos más recientes (20%) para evaluación
    y_real = df['volume_m3'].iloc[split:]
    y_pred = df['pred'].iloc[split:]

    # Métricas de error
    mae = mean_absolute_error(y_real, y_pred)
    rmse = sqrt(mean_squared_error(y_real, y_pred))
    r2 = r2_score(y_real, y_pred)

    return {
        "Ventana_dias": ventana,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    }


# --------------------------------------------------
# FORECAST FUTURO
# --------------------------------------------------
def forecast_promedio_movil(df, ventana, dias=180):
    """
    Genera un pronóstico futuro usando el
    promedio móvil de la ventana seleccionada.

    El valor diario proyectado corresponde al
    promedio de los últimos 'ventana' días reales.
    """

    promedio = df['volume_m3'].tail(ventana).mean()
    last_date = df['fecha'].max()

    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=dias
    )

    forecast = pd.DataFrame({
        "fecha": future_dates,
        "pred_volume_m3": promedio
    })

    return forecast


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== MODELO C1 | PROMEDIO MÓVIL ===")

    df = cargar_daily_demand()

    if df.empty or len(df) < max(VENTANAS):
        print("No hay suficientes datos para evaluar todas las ventanas.")
        return

    resultados = []

    # Evaluación de todas las ventanas definidas
    for v in VENTANAS:
        res = evaluar_promedio_movil(df, v)
        resultados.append(res)

    resultados_df = pd.DataFrame(resultados).sort_values("MAE")

    print("\n--- Resultados comparativos (ordenados por MAE) ---")
    print(resultados_df)

    # Selección de la mejor ventana según MAE
    mejor = resultados_df.iloc[0]
    print("\n--- Mejor ventana según MAE ---")
    print(mejor)

    # Forecast con la ventana óptima
    forecast = forecast_promedio_movil(
        df,
        int(mejor['Ventana_dias']),
        dias=180
    )

    print("\n--- Pronóstico inicial (primeros 5 días) ---")
    print(forecast.head())

    print("\nModelo de Promedio Móvil ejecutado correctamente.")


if __name__ == "__main__":
    main()
