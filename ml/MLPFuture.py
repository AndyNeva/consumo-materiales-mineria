#!/usr/bin/env python3
"""
Modelo para predecir consumo futuro de concreto (volumen_m3) a partir de fechas.
Genera un modelo regresor y lo exporta como Pfuture.pkl.
"""

import sys
from pathlib import Path
from datetime import timedelta
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from math import sqrt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# Añadir raíz del proyecto al path para usar utils
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.loaders import cargar_datos_tabla

MODEL_PATH = ROOT_DIR / "ml" / "Pfuture.pkl"


def load_despachos() -> pd.DataFrame:
    """Carga los despachos y devuelve un DataFrame."""
    datos = cargar_datos_tabla("despachos")

    return pd.DataFrame(datos)


def prepare_daily_series(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa por fecha para obtener consumo diario y genera features temporales."""
    df = df.copy()
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['fecha', 'volumen_m3'])
    df['volumen_m3'] = pd.to_numeric(df['volumen_m3'], errors='coerce')
    df = df.dropna(subset=['volumen_m3'])

    # Consumo diario total
    daily = df.groupby('fecha', as_index=False)['volumen_m3'].sum()

    # Features temporales
    daily['anio'] = daily['fecha'].dt.year
    daily['mes'] = daily['fecha'].dt.month
    daily['semana'] = daily['fecha'].dt.isocalendar().week.astype(int)
    daily['dia'] = daily['fecha'].dt.day
    daily['dia_semana'] = daily['fecha'].dt.dayofweek

    # Lags simples para capturar tendencia reciente
    daily = daily.sort_values('fecha').reset_index(drop=True)
    for lag in [1, 7, 14, 28]:
        daily[f'lag_{lag}'] = daily['volumen_m3'].shift(lag)

    # Imputar lags con mediana inicial
    med = daily['volumen_m3'].median()
    for col in [c for c in daily.columns if c.startswith('lag_')]:
        daily[col] = daily[col].fillna(med)

    # Garantizar ausencia de nulos en features numéricos
    feature_cols = [c for c in daily.columns if c != 'fecha']
    daily[feature_cols] = daily[feature_cols].fillna(med)

    return daily


def split_train_test(daily: pd.DataFrame):
    """Divide en train/test preservando el orden temporal."""
    feature_cols = [c for c in daily.columns if c not in ['fecha', 'volumen_m3']]
    X = daily[feature_cols]
    y = daily['volumen_m3']

    # División temporal: 80% primeros registros para train
    split_idx = int(len(daily) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    return X_train, X_test, y_train, y_test, feature_cols


def train_model(X_train, y_train):
    """Entrena un GradientBoostingRegressor."""
    model = GradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)
    return model


def evaluate(model, X_test, y_test):
    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    return {
        "r2": r2_score(y_test, preds),
        "mae": mean_absolute_error(y_test, preds),
        "rmse": sqrt(mse),
    }


def forecast_future(model, feature_cols, last_date: pd.Timestamp, lag_fill: float, days_ahead: int = 365):
    """Genera un DataFrame con predicciones para fechas futuras."""
    future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=days_ahead, freq='D')
    fut = pd.DataFrame({"fecha": future_dates})
    fut['anio'] = fut['fecha'].dt.year
    fut['mes'] = fut['fecha'].dt.month
    fut['semana'] = fut['fecha'].dt.isocalendar().week.astype(int)
    fut['dia'] = fut['fecha'].dt.day
    fut['dia_semana'] = fut['fecha'].dt.dayofweek

    # Para lags futuras usamos el valor mediano histórico como aproximación conservadora
    fut['lag_1'] = fut['lag_7'] = fut['lag_14'] = fut['lag_28'] = lag_fill

    # Alinear columnas para el modelo sin perder 'fecha'
    fut_features = fut.reindex(columns=feature_cols, fill_value=lag_fill)
    fut['pred_volumen_m3'] = model.predict(fut_features)
    return fut


def main():
    print("=== Entrenando modelo de consumo futuro ===")
    df = load_despachos()
    if df.empty:
        print("No hay datos en la tabla despachos")
        return

    daily = prepare_daily_series(df)
    if len(daily) < 30:
        print("Muy pocos datos para entrenar (menos de 30 días)")
        return
    X_train, X_test, y_train, y_test, feature_cols = split_train_test(daily)

    model = train_model(X_train, y_train)
    metrics = evaluate(model, X_test, y_test)

    # Guardar modelo
    joblib.dump({"model": model, "features": feature_cols}, MODEL_PATH)
    print(f"Modelo guardado en {MODEL_PATH}")

    # Forecast 1 año
    last_date = daily['fecha'].max()
    lag_fill = float(daily['volumen_m3'].median())
    fut = forecast_future(model, feature_cols, last_date, lag_fill=lag_fill, days_ahead=365)

    print("--- Métricas ---")
    print(f"R2:   {metrics['r2']:.4f}")
    print(f"MAE:  {metrics['mae']:.2f} m3")
    print(f"RMSE: {metrics['rmse']:.2f} m3")
    print(f"Última fecha histórica: {last_date.date()}")
    print(f"Primera fecha futura:   {fut['fecha'].min().date()}")
    print(f"Última fecha futura:    {fut['fecha'].max().date()}")

    # Mostrar primeras filas de pronóstico
    print("\nPronóstico inicial:")
    print(fut[['fecha', 'pred_volumen_m3']].head())


if __name__ == "__main__":
    main()
