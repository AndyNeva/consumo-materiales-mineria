import pickle
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor

# Cargar el archivo CSV desde la carpeta data/processed
BASE_DIR = Path(__file__).resolve().parent
DATOS = BASE_DIR / "data" / "processed" / "DatosLimpios.csv"

if not DATOS.exists():
    raise FileNotFoundError(f"No se encontró el archivo de datos esperado en {DATOS}")

df = pd.read_csv(DATOS)

# Eliminar datos faltantes
df = df.dropna()

# Convertir FECHA a formato numérico (días desde la fecha mínima)
df['FECHA'] = pd.to_datetime(df['FECHA'], format='%m/%d/%Y', errors='coerce')
df = df.dropna(subset=['FECHA'])  # Eliminar filas con fechas inválidas

# Convertir fecha a número de días desde la fecha mínima del dataset
fecha_min = df['FECHA'].min()
df['FECHA_NUMERICO'] = (df['FECHA'] - fecha_min).dt.days

# Verificar que tenemos suficientes datos
if len(df) < 10:
    raise ValueError(f"No hay suficientes datos para entrenar el modelo. Se encontraron solo {len(df)} filas válidas.")

print(f"\n=== Información del Dataset ===")
print(f"Total de registros: {len(df)}")
print(f"Columnas: {list(df.columns)}")
print(f"Rango de fechas: {df['FECHA'].min()} a {df['FECHA'].max()}")
print(f"Días totales: {df['FECHA_NUMERICO'].max()}")

# Seleccionar las columnas relevantes para el modelo (regresión multivariable)
# Variables independientes: Arena, Grava, Cemento
# Variable dependiente: FECHA (convertida a días numéricos)
features = ['Arena (kg)', 'Grava (kg)', 'Cemento (kg)']
target = 'FECHA_NUMERICO'

# Verificar que las columnas existen
columnas_necesarias = features + [target]
columnas_faltantes = [col for col in columnas_necesarias if col not in df.columns]
if columnas_faltantes:
    raise ValueError(f"Columnas faltantes en el dataset: {columnas_faltantes}")

X = df[features].values
y = df[target].values

print(f"\n=== Configuración del Modelo ===")
print(f"Variables independientes: {', '.join(features)}")
print(f"Variable dependiente: {target}")
print(f"Forma de X: {X.shape}")
print(f"Forma de y: {y.shape}")

# Escalar los datos
scaler_X = StandardScaler()
scaler_y = StandardScaler()
X_scaled = scaler_X.fit_transform(X)
y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).ravel()

# Dividir los datos en entrenamiento y validación
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_scaled, test_size=0.2, random_state=42, shuffle=True
)

print(f"Datos de entrenamiento: {len(X_train)}")
print(f"Datos de validación: {len(X_test)}")

# Crear y entrenar múltiples modelos
print(f"\n=== Entrenando Modelos ===")

modelos = {
    'Random Forest': RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
    'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42),
    'XGBoost': XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, n_jobs=-1)
}

resultados = {}

for nombre, modelo in modelos.items():
    print(f"\nEntrenando {nombre}...")
    modelo.fit(X_train, y_train)
    
    # Predicciones
    y_pred_train = modelo.predict(X_train)
    y_pred_test = modelo.predict(X_test)
    
    # Desescalar predicciones
    y_pred_train_original = scaler_y.inverse_transform(y_pred_train.reshape(-1, 1)).ravel()
    y_pred_test_original = scaler_y.inverse_transform(y_pred_test.reshape(-1, 1)).ravel()
    y_train_original = scaler_y.inverse_transform(y_train.reshape(-1, 1)).ravel()
    y_test_original = scaler_y.inverse_transform(y_test.reshape(-1, 1)).ravel()
    
    # Calcular métricas
    mse_train = mean_squared_error(y_train_original, y_pred_train_original)
    mse_test = mean_squared_error(y_test_original, y_pred_test_original)
    r2_train = r2_score(y_train_original, y_pred_train_original)
    r2_test = r2_score(y_test_original, y_pred_test_original)
    mae_test = mean_absolute_error(y_test_original, y_pred_test_original)
    rmse_test = np.sqrt(mse_test)
    
    resultados[nombre] = {
        'modelo': modelo,
        'mse_train': mse_train,
        'mse_test': mse_test,
        'r2_train': r2_train,
        'r2_test': r2_test,
        'mae_test': mae_test,
        'rmse_test': rmse_test,
        'y_pred': y_pred_test_original
    }
    
    print(f"  R² Entrenamiento: {r2_train:.4f}")
    print(f"  R² Validación: {r2_test:.4f}")
    print(f"  RMSE: {rmse_test:.4f}")
    print(f"  MAE: {mae_test:.4f}")

# Seleccionar el mejor modelo basado en R² de validación
mejor_nombre = max(resultados, key=lambda k: resultados[k]['r2_test'])
mejor_modelo = resultados[mejor_nombre]['modelo']
mejores_metricas = resultados[mejor_nombre]

print(f"\n=== Mejor Modelo: {mejor_nombre} ===")
print(f"R² Validación: {mejores_metricas['r2_test']:.4f}")
print(f"RMSE: {mejores_metricas['rmse_test']:.4f}")
print(f"MAE: {mejores_metricas['mae_test']:.4f}")

# Calcular MAPE
y_test_original = scaler_y.inverse_transform(y_test.reshape(-1, 1)).ravel()
predictions_original = mejores_metricas['y_pred']
mape = np.mean(np.abs((y_test_original - predictions_original) / (y_test_original + 1e-8))) * 100
print(f"MAPE: {mape:.2f}%")

# Guardar el mejor modelo en un archivo .pkl
MODEL_PATH = BASE_DIR / 'modelo_regresion_fecha.pkl'
with open(MODEL_PATH, 'wb') as file:
    pickle.dump({
        'model': mejor_modelo,
        'model_name': mejor_nombre,
        'scaler_X': scaler_X,
        'scaler_y': scaler_y,
        'features': features,
        'target': target,
        'fecha_min': fecha_min,  # Guardar la fecha mínima para conversiones futuras
        'metricas': {
            'mse': mejores_metricas['mse_test'],
            'rmse': mejores_metricas['rmse_test'],
            'r2': mejores_metricas['r2_test'],
            'mae': mejores_metricas['mae_test'],
            'mape': mape
        }
    }, file)
print(f'\n✓ Modelo guardado exitosamente en: {MODEL_PATH}')

# Función para predicciones
def predecir_fecha(arena, grava, cemento):
    """
    Predice la fecha (en días desde fecha mínima) dados los materiales.
    
    Args:
        arena (float): Cantidad de arena en kg
        grava (float): Cantidad de grava en kg
        cemento (float): Cantidad de cemento en kg
    
    Returns:
        float: Predicción de fecha en días numéricos
    """
    try:
        # Crear array con los valores de entrada
        entrada = np.array([[arena, grava, cemento]])
        
        # Escalar los datos
        entrada_escalada = scaler_X.transform(entrada)
        
        # Realizar predicción
        prediccion_escalada = mejor_modelo.predict(entrada_escalada)
        prediccion = scaler_y.inverse_transform(prediccion_escalada.reshape(-1, 1))[0][0]
        
        # Asegurar que el valor no sea negativo
        prediccion = max(prediccion, 0)
        
        return prediccion
    except Exception as e:
        print(f"Error en la predicción: {e}")
        return None

# Ejemplos de predicción
print(f'\n=== Ejemplos de Predicciones ===')
ejemplos = [
    (150, 300, 50),
    (200, 400, 75),
    (100, 250, 40)
]

for arena, grava, cemento in ejemplos:
    fecha_predicha = predecir_fecha(arena, grava, cemento)
    if fecha_predicha is not None:
        # Convertir días a fecha real
        fecha_real = fecha_min + pd.Timedelta(days=int(fecha_predicha))
        print(f'Arena: {arena} kg, Grava: {grava} kg, Cemento: {cemento} kg → Fecha predicha: {fecha_real.strftime("%Y-%m-%d")} (día {fecha_predicha:.0f})')

# Gráfico 1: Valores reales vs predicciones
plt.figure(figsize=(15, 10))

# Comparación de modelos
plt.subplot(2, 3, 1)
for nombre, resultado in resultados.items():
    y_pred = resultado['y_pred']
    r2 = resultado['r2_test']
    plt.scatter(y_test_original, y_pred, alpha=0.5, label=f'{nombre} (R²={r2:.3f})', s=30)
plt.plot([y_test_original.min(), y_test_original.max()], 
         [y_test_original.min(), y_test_original.max()], 
         'r--', lw=2, label='Predicción perfecta')
plt.xlabel('Valores Reales (días)', fontweight='bold')
plt.ylabel('Predicciones (días)', fontweight='bold')
plt.title('Comparación de Modelos', fontweight='bold')
plt.legend(fontsize=8)
plt.grid(True, alpha=0.3)

# Mejor modelo
plt.subplot(2, 3, 2)
plt.scatter(y_test_original, predictions_original, alpha=0.6, edgecolors='k', c='blue')
plt.plot([y_test_original.min(), y_test_original.max()], 
         [y_test_original.min(), y_test_original.max()], 
         'r--', lw=2, label='Predicción perfecta')
plt.xlabel('Valores Reales (días)', fontweight='bold')
plt.ylabel('Predicciones (días)', fontweight='bold')
plt.title(f'Mejor Modelo: {mejor_nombre}\nR²={mejores_metricas["r2_test"]:.4f}', fontweight='bold')
plt.legend()
plt.grid(True, alpha=0.3)

# Residuos
plt.subplot(2, 3, 3)
residuos = y_test_original - predictions_original
plt.scatter(predictions_original, residuos, alpha=0.6, edgecolors='k', c='green')
plt.axhline(y=0, color='r', linestyle='--', lw=2)
plt.xlabel('Predicciones (días)', fontweight='bold')
plt.ylabel('Residuos (días)', fontweight='bold')
plt.title('Gráfico de Residuos', fontweight='bold')
plt.grid(True, alpha=0.3)

# Distribución de residuos
plt.subplot(2, 3, 4)
plt.hist(residuos, bins=20, alpha=0.7, color='purple', edgecolor='black')
plt.xlabel('Residuos (días)', fontweight='bold')
plt.ylabel('Frecuencia', fontweight='bold')
plt.title('Distribución de Residuos', fontweight='bold')
plt.grid(True, alpha=0.3, axis='y')

# Importancia de características (solo para modelos de árbol)
if mejor_nombre in ['Random Forest', 'Gradient Boosting', 'XGBoost']:
    plt.subplot(2, 3, 5)
    importancias = mejor_modelo.feature_importances_
    indices = np.argsort(importancias)[::-1]
    plt.barh([features[i] for i in indices], importancias[indices], 
             color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    plt.xlabel('Importancia', fontweight='bold')
    plt.title('Importancia de Variables', fontweight='bold')
    plt.grid(True, alpha=0.3, axis='x')

# Métricas comparativas
plt.subplot(2, 3, 6)
nombres_modelos = list(resultados.keys())
r2_scores = [resultados[n]['r2_test'] for n in nombres_modelos]
colors_bar = ['green' if n == mejor_nombre else 'skyblue' for n in nombres_modelos]
plt.barh(nombres_modelos, r2_scores, color=colors_bar, edgecolor='black')
plt.xlabel('R² Score', fontweight='bold')
plt.title('Comparación de R² por Modelo', fontweight='bold')
plt.grid(True, alpha=0.3, axis='x')
plt.xlim(0, 1)

plt.tight_layout()
plt.savefig(BASE_DIR / 'prediccion_fecha.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Gráfico guardado en: {BASE_DIR / 'prediccion_fecha.png'}")

# Gráfico 2: Correlaciones
plt.figure(figsize=(8, 6))
correlaciones = []
for i, feature in enumerate(features):
    corr = np.corrcoef(X[:, i], y)[0, 1]
    correlaciones.append(corr)

plt.barh(features, correlaciones, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
plt.xlabel('Correlación con Fecha', fontweight='bold')
plt.title('Correlación de Variables con la Fecha', fontweight='bold')
plt.grid(True, alpha=0.3, axis='x')
plt.tight_layout()
plt.savefig(BASE_DIR / 'correlaciones_fecha.png', dpi=300, bbox_inches='tight')
print(f"✓ Gráfico guardado en: {BASE_DIR / 'correlaciones_fecha.png'}")

print(f"\n{'='*50}")
print(f"✓ Entrenamiento completado exitosamente")
print(f"✓ Modelo seleccionado: {mejor_nombre}")
print(f"✓ R² Score: {mejores_metricas['r2_test']:.4f}")
print(f"{'='*50}")

plt.show()