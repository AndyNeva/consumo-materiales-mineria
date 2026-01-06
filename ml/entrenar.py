import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

# Asegura que se puedan importar los módulos del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.loaders import cargar_datos_tabla

# Configuración de rutas de artefactos
MODEL_PATH = ROOT_DIR / "ml" / "modelo_hormigon.pkl"
SCALER_PATH = ROOT_DIR / "ml" / "scaler_hormigon.pkl"


def cargar_datos():
    """Carga los datos desde la base de datos"""
    datos = cargar_datos_tabla("despachos")
    return pd.DataFrame(datos)

def preparar_datos(df):
    """Limpia y genera características para el modelo.

    Objetivo: predecir `asentamiento_final_cm` usando información temporal,
    humedad de arena, temperatura, volumen y categorías principales.
    """

    # Normalizar tipos y eliminar filas sin objetivo
    df = df.copy()
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['fecha', 'asentamiento_final_cm'])

    # Imputar valores faltantes numéricos con mediana
    for col in ['volumen_m3', 'arena_humedad_pct', 'temperatura_c']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col].fillna(df[col].median(), inplace=True)

    # Variables temporales
    df['anio'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    df['dia'] = df['fecha'].dt.day
    df['dia_semana'] = df['fecha'].dt.dayofweek

    # Selección de columnas para no disparar la dimensionalidad
    base_cols = ['volumen_m3', 'arena_humedad_pct', 'temperatura_c', 'anio', 'mes', 'dia', 'dia_semana']
    cat_cols = ['fuente_cemento', 'diseno_mezcla', 'turno']

    # One-hot encoding de categóricas (drop_first para evitar colinealidad)
    df_model = pd.get_dummies(df[base_cols + cat_cols], columns=cat_cols, drop_first=True)

    X = df_model.values
    y = df['asentamiento_final_cm'].values

    return X, y, df

def entrenar_modelo(X, y):
    """Entrena la red neuronal"""
    # División 80-20
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Normalización
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Crear y entrenar red neuronal
    modelo = MLPRegressor(
        hidden_layer_sizes=(100, 50, 25),
        activation='relu',
        solver='adam',
        max_iter=1000,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1
    )
    
    print("Entrenando modelo...")
    modelo.fit(X_train_scaled, y_train)
    
    # Evaluación
    y_pred_train = modelo.predict(X_train_scaled)
    y_pred_test = modelo.predict(X_test_scaled)
    
    print("\n=== RESULTADOS DEL ENTRENAMIENTO ===")
    print(f"R² Training: {r2_score(y_train, y_pred_train):.4f}")
    print(f"R² Testing: {r2_score(y_test, y_pred_test):.4f}")
    print(f"MSE Testing: {mean_squared_error(y_test, y_pred_test):.4f}")
    print(f"MAE Testing: {mean_absolute_error(y_test, y_pred_test):.4f}")
    print(f"Muestras entrenamiento: {len(X_train)}")
    print(f"Muestras prueba: {len(X_test)}")
    
    return modelo, scaler, X_test_scaled, y_test

def guardar_modelo(modelo, scaler):
    """Guarda el modelo y scaler en archivos .pkl"""
    joblib.dump(modelo, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"\n Modelo guardado en: {MODEL_PATH}")
    print(f" Scaler guardado en: {SCALER_PATH}")

def main():
    # Cargar datos
    df = cargar_datos()
    if df is None or df.empty:
        print("No hay datos disponibles")
        return
    
    print(f"Datos cargados: {len(df)} registros")
    
    # Preparar datos
    X, y, df = preparar_datos(df)
    
    # Entrenar modelo
    modelo, scaler, X_test, y_test = entrenar_modelo(X, y)
    
    # Guardar modelo
    guardar_modelo(modelo, scaler)
    
    print("\n Proceso completado exitosamente")

if __name__ == "__main__":
    main()