import pickle
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from xgboost import XGBRegressor

# Cargar el archivo CSV desde el mismo directorio del script
BASE_DIR = Path(__file__).resolve().parent
DATOS = BASE_DIR / "DatosLimpios.csv"

if not DATOS.exists():
    raise FileNotFoundError(f"No se encontró el archivo de datos esperado en {DATOS}")

df = pd.read_csv(DATOS)

# Eliminar datos faltantes
df = df.dropna()

# Convertir FECHA a formato datetime y crear variables de tiempo
df['FECHA'] = pd.to_datetime(df['FECHA'], format='%m/%d/%Y', errors='coerce')
df = df.dropna(subset=['FECHA'])  # Eliminar filas con fechas inválidas

# Referencia temporal
fecha_min = df['FECHA'].min()
df['FECHA_NUMERICO'] = (df['FECHA'] - fecha_min).dt.days
df['FECHA_NUMERICO_SQ'] = df['FECHA_NUMERICO'] ** 2
df['FECHA_NUMERICO_CU'] = df['FECHA_NUMERICO'] ** 3

# Variables de calendario
df['MES'] = df['FECHA'].dt.month
df['DIA_ANIO'] = df['FECHA'].dt.dayofyear
df['SEMANA_ANIO'] = df['FECHA'].dt.isocalendar().week.astype(int)
df['ANIO'] = df['FECHA'].dt.year

# Codificación cíclica (captura estacionalidad)
df['MES_SIN'] = np.sin(2 * np.pi * df['MES'] / 12)
df['MES_COS'] = np.cos(2 * np.pi * df['MES'] / 12)
df['DIA_SIN'] = np.sin(2 * np.pi * df['DIA_ANIO'] / 365.25)
df['DIA_COS'] = np.cos(2 * np.pi * df['DIA_ANIO'] / 365.25)
df['SEMANA_SIN'] = np.sin(2 * np.pi * df['SEMANA_ANIO'] / 52)
df['SEMANA_COS'] = np.cos(2 * np.pi * df['SEMANA_ANIO'] / 52)

# Variables categóricas simplificadas
df['TURNO_BIN'] = df['TURNO'].str.upper().eq('DIA').astype(int)
top_diseno = df['Diseño de la Mezcla'].value_counts().nlargest(10).index.tolist()
df['DISENO_TOP'] = df['Diseño de la Mezcla'].where(df['Diseño de la Mezcla'].isin(top_diseno), 'OTROS')

# Verificar que tenemos suficientes datos
if len(df) < 10:
    raise ValueError(f"No hay suficientes datos para entrenar el modelo. Se encontraron solo {len(df)} filas válidas.")

print(f"\n=== Información del Dataset ===")
print(f"Total de registros: {len(df)}")
print(f"Columnas: {list(df.columns)}")
print(f"Rango de fechas: {df['FECHA'].min()} a {df['FECHA'].max()}")
print(f"Días totales: {df['FECHA_NUMERICO'].max()}")

# Seleccionar columnas relevantes para el modelo
# Variables independientes: tiempo + numéricas de proceso + categóricas codificadas
numeric_extras = [
    'Volumen (m3)', 'Humedad arena (%)', 'Agua (kg)',
    'RHEO 1000 (kg)', 'BASF 719 (kg)', 'Delvo (litros)',
    'MasterGlenium 7950', 'MasterGlenium 7970', 'Sika PP 48 (kg)-BARCHIP'
]

feature_cols = [
    'FECHA_NUMERICO', 'FECHA_NUMERICO_SQ', 'FECHA_NUMERICO_CU',
    'MES', 'DIA_ANIO', 'SEMANA_ANIO', 'ANIO',
    'MES_SIN', 'MES_COS', 'DIA_SIN', 'DIA_COS', 'SEMANA_SIN', 'SEMANA_COS',
    'TURNO_BIN'
] + numeric_extras

targets = ['Arena (kg)', 'Grava (kg)', 'Cemento (kg)']

# One-hot de diseño top
dummies_diseno = pd.get_dummies(df['DISENO_TOP'], prefix='DISENO')
df_model = pd.concat([df, dummies_diseno], axis=1)
feature_cols_extended = feature_cols + list(dummies_diseno.columns)

# Verificar columnas
columnas_necesarias = feature_cols_extended + targets
columnas_faltantes = [col for col in columnas_necesarias if col not in df_model.columns]
if columnas_faltantes:
    raise ValueError(f"Columnas faltantes en el dataset: {columnas_faltantes}")

X_raw = df_model[feature_cols_extended].values
y = df_model[targets].values  # Múltiples salidas

print(f"\n=== Configuración del Modelo ===")
print(f"Variables independientes: {', '.join(feature_cols_extended)}")
print(f"Variables dependientes: {', '.join(targets)}")
print(f"Forma de X: {X_raw.shape}")
print(f"Forma de y: {y.shape}")

# Dividir los datos en entrenamiento y validación (manteniendo fechas)
X_train_raw, X_test_raw, y_train, y_test, fechas_train, fechas_test = train_test_split(
    X_raw, y, df_model['FECHA'].values, test_size=0.2, random_state=42, shuffle=True
)

# Escalar los datos usando solo entrenamiento
scaler_X = StandardScaler()
scaler_y = StandardScaler()
X_train = scaler_X.fit_transform(X_train_raw)
X_test = scaler_X.transform(X_test_raw)
y_train = scaler_y.fit_transform(y_train)
y_test = scaler_y.transform(y_test)

print(f"Datos de entrenamiento: {len(X_train)}")
print(f"Datos de validación: {len(X_test)}")

# Crear y entrenar múltiples modelos
print(f"\n=== Entrenando Modelos ===")

modelos = {
    'Random Forest': MultiOutputRegressor(
        RandomForestRegressor(
            n_estimators=400,
            max_depth=None,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
    ),
    'Gradient Boosting': MultiOutputRegressor(
        GradientBoostingRegressor(
            n_estimators=400,
            max_depth=4,
            learning_rate=0.05,
            random_state=42
        )
    ),
    'XGBoost': MultiOutputRegressor(
        XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='reg:squarederror',
            random_state=42,
            n_jobs=-1
        )
    )
}

resultados = {}

for nombre, modelo in modelos.items():
    print(f"\nEntrenando {nombre}...")
    modelo.fit(X_train, y_train)
    
    # Predicciones
    y_pred_train = modelo.predict(X_train)
    y_pred_test = modelo.predict(X_test)
    
    # Desescalar predicciones
    y_pred_train_original = scaler_y.inverse_transform(y_pred_train)
    y_pred_test_original = scaler_y.inverse_transform(y_pred_test)
    y_train_original = scaler_y.inverse_transform(y_train)
    y_test_original = scaler_y.inverse_transform(y_test)
    
    # Calcular métricas (promedio de todas las salidas)
    mse_train = mean_squared_error(y_train_original, y_pred_train_original)
    mse_test = mean_squared_error(y_test_original, y_pred_test_original)
    r2_train = r2_score(y_train_original, y_pred_train_original, multioutput='variance_weighted')
    r2_test = r2_score(y_test_original, y_pred_test_original, multioutput='variance_weighted')
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

# Calcular MAPE promedio seguro (evita divisiones por valores cercanos a cero)
y_test_original = scaler_y.inverse_transform(y_test)
predictions_original = mejores_metricas['y_pred']
eps = 1e-3
mape_por_objetivo = []
for i, objetivo in enumerate(targets):
    real = np.abs(y_test_original[:, i])
    pred = predictions_original[:, i]
    mape_i = np.mean(np.abs((real - pred) / np.maximum(real, eps))) * 100
    mape_por_objetivo.append(mape_i)
mape = np.mean(mape_por_objetivo)
print(f"MAPE promedio: {mape:.2f}%")
for obj, m in zip(targets, mape_por_objetivo):
    print(f"  - {obj}: {m:.2f}%")

# Guardar el mejor modelo en un archivo .pkl
MODEL_PATH = BASE_DIR / 'modelo_prediccion_materiales.pkl'
with open(MODEL_PATH, 'wb') as file:
    pickle.dump({
        'model': mejor_modelo,
        'model_name': mejor_nombre,
        'scaler_X': scaler_X,
        'scaler_y': scaler_y,
        'features': feature_cols_extended,
        'targets': targets,
        'top_diseno': top_diseno,
        'dummies_cols': list(dummies_diseno.columns),
        'fecha_min': fecha_min,  # Guardar la fecha mínima para conversiones futuras
        'fecha_max': df['FECHA'].max(),  # Guardar fecha máxima del entrenamiento
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
def predecir_materiales(
    fecha_str,
    turno='DIA',
    diseno='OTROS',
    volumen=0.0,
    humedad=0.0,
    agua=0.0,
    rheo=0.0,
    basf=0.0,
    delvo=0.0,
    mg7950=0.0,
    mg7970=0.0,
    sika=0.0
):
    """Predice las cantidades de materiales necesarios para una fecha futura.

    Args:
        fecha_str: Fecha en formato 'YYYY-MM-DD'
        turno: 'DIA' o 'NOCHE'
        diseno: nombre del diseño de mezcla (se mapea al top 10, si no, 'OTROS')
        volumen: Volumen (m3)
        humedad: Humedad arena (%)
        agua: Agua (kg)
        rheo: RHEO 1000 (kg)
        basf: BASF 719 (kg)
        delvo: Delvo (litros)
        mg7950: MasterGlenium 7950
        mg7970: MasterGlenium 7970
        sika: Sika PP 48 (kg)-BARCHIP
    """
    try:
        fecha_prediccion = pd.to_datetime(fecha_str)

        # Features temporales
        dias_desde_inicio = (fecha_prediccion - fecha_min).days
        mes = fecha_prediccion.month
        dia_anio = fecha_prediccion.dayofyear
        semana_anio = fecha_prediccion.isocalendar().week
        anio = fecha_prediccion.year

        turno_bin = str(turno).upper() == 'DIA'

        # Diseño top
        diseno_mapeado = diseno if diseno in top_diseno else 'OTROS'
        dummies_input = {col: 0 for col in dummies_diseno.columns}
        col_name = f"DISENO_{diseno_mapeado}"
        if col_name in dummies_input:
            dummies_input[col_name] = 1

        base_features = [
            dias_desde_inicio,
            dias_desde_inicio ** 2,
            dias_desde_inicio ** 3,
            mes,
            dia_anio,
            semana_anio,
            anio,
            np.sin(2 * np.pi * mes / 12),
            np.cos(2 * np.pi * mes / 12),
            np.sin(2 * np.pi * dia_anio / 365.25),
            np.cos(2 * np.pi * dia_anio / 365.25),
            np.sin(2 * np.pi * semana_anio / 52),
            np.cos(2 * np.pi * semana_anio / 52),
            int(turno_bin),
            volumen,
            humedad,
            agua,
            rheo,
            basf,
            delvo,
            mg7950,
            mg7970,
            sika
        ]

        entrada_list = base_features + [dummies_input[col] for col in dummies_diseno.columns]
        entrada = np.array([entrada_list])

        entrada_escalada = scaler_X.transform(entrada)
        prediccion_escalada = mejor_modelo.predict(entrada_escalada)
        prediccion = scaler_y.inverse_transform(prediccion_escalada)[0]

        prediccion = np.maximum(prediccion, 0)

        return {
            'fecha': fecha_str,
            'Arena (kg)': round(prediccion[0], 2),
            'Grava (kg)': round(prediccion[1], 2),
            'Cemento (kg)': round(prediccion[2], 2)
        }
    except Exception as e:
        print(f"Error en la predicción: {e}")
        return None

# Ejemplos de predicción para fechas futuras
print(f'\n=== Predicciones para Fechas Futuras ===')
print(f'Fecha máxima de entrenamiento: {df["FECHA"].max().strftime("%Y-%m-%d")}')
print(f'\nPredicciones:')

fechas_futuras = [
    {
        'fecha_str': '2026-01-15', 'turno': 'DIA', 'diseno': top_diseno[0] if top_diseno else 'OTROS',
        'volumen': 6, 'humedad': 0.05, 'agua': 950, 'rheo': 50, 'basf': 18, 'delvo': 6, 'mg7950': 0, 'mg7970': 0, 'sika': 24
    },
    {
        'fecha_str': '2026-02-15', 'turno': 'NOCHE', 'diseno': top_diseno[1] if len(top_diseno) > 1 else 'OTROS',
        'volumen': 6, 'humedad': 0.05, 'agua': 930, 'rheo': 50, 'basf': 18, 'delvo': 6, 'mg7950': 0, 'mg7970': 0, 'sika': 24
    },
    {
        'fecha_str': '2026-06-15', 'turno': 'DIA', 'diseno': top_diseno[2] if len(top_diseno) > 2 else 'OTROS',
        'volumen': 5, 'humedad': 0.06, 'agua': 880, 'rheo': 45, 'basf': 16, 'delvo': 5, 'mg7950': 0, 'mg7970': 0, 'sika': 22
    }
]

for params in fechas_futuras:
    resultado = predecir_materiales(**params)
    if resultado is not None:
        print(f"\nFecha: {resultado['fecha']}")
        print(f"  • Arena:   {resultado['Arena (kg)']:>10,.2f} kg")
        print(f"  • Grava:   {resultado['Grava (kg)']:>10,.2f} kg")
        print(f"  • Cemento: {resultado['Cemento (kg)']:>10,.2f} kg")

# Gráficos detallados por material
fig, axes = plt.subplots(3, 3, figsize=(18, 15))
fig.suptitle(f'Predicción de Consumo de Materiales - Modelo: {mejor_nombre}', fontsize=16, fontweight='bold')

# Para cada material (Arena, Grava, Cemento)
for idx, material in enumerate(targets):
    # Gráfico 1: Valores reales vs predicciones
    ax1 = axes[idx, 0]
    ax1.scatter(y_test_original[:, idx], predictions_original[:, idx], alpha=0.6, edgecolors='k', c='blue', s=40)
    min_val = min(y_test_original[:, idx].min(), predictions_original[:, idx].min())
    max_val = max(y_test_original[:, idx].max(), predictions_original[:, idx].max())
    ax1.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2, label='Predicción perfecta')
    ax1.set_xlabel('Valores Reales (kg)', fontweight='bold')
    ax1.set_ylabel('Predicciones (kg)', fontweight='bold')
    ax1.set_title(f'{material}\nR² = {r2_score(y_test_original[:, idx], predictions_original[:, idx]):.4f}', 
                  fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Gráfico 2: Residuos
    ax2 = axes[idx, 1]
    residuos_material = y_test_original[:, idx] - predictions_original[:, idx]
    ax2.scatter(predictions_original[:, idx], residuos_material, alpha=0.6, edgecolors='k', c='green', s=40)
    ax2.axhline(y=0, color='r', linestyle='--', lw=2)
    ax2.set_xlabel('Predicciones (kg)', fontweight='bold')
    ax2.set_ylabel('Residuos (kg)', fontweight='bold')
    ax2.set_title(f'Residuos - {material}', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Gráfico 3: Distribución de residuos
    ax3 = axes[idx, 2]
    ax3.hist(residuos_material, bins=20, alpha=0.7, color='purple', edgecolor='black')
    ax3.set_xlabel('Residuos (kg)', fontweight='bold')
    ax3.set_ylabel('Frecuencia', fontweight='bold')
    ax3.set_title(f'Distribución de Residuos - {material}', fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(BASE_DIR / 'prediccion_materiales_detallado.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Gráfico detallado guardado en: {BASE_DIR / 'prediccion_materiales_detallado.png'}")

# Gráfico de series de tiempo
plt.figure(figsize=(15, 8))
X_test_inverso = scaler_X.inverse_transform(X_test)
X_test_dias = X_test_inverso[:, 0]
X_test_fechas = [fecha_min + pd.Timedelta(days=int(d)) for d in X_test_dias]

for idx, material in enumerate(targets):
    plt.subplot(3, 1, idx + 1)
    plt.scatter(X_test_fechas, y_test_original[:, idx], alpha=0.5, label='Real', s=30)
    plt.scatter(X_test_fechas, predictions_original[:, idx], alpha=0.5, label='Predicción', s=30)
    plt.xlabel('Fecha', fontweight='bold')
    plt.ylabel('Cantidad (kg)', fontweight='bold')
    plt.title(f'{material} - Real vs Predicción', fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

plt.tight_layout()
plt.savefig(BASE_DIR / 'serie_tiempo_materiales.png', dpi=300, bbox_inches='tight')
print(f"✓ Gráfico de series de tiempo guardado en: {BASE_DIR / 'serie_tiempo_materiales.png'}")

# Gráfico de métricas comparativas
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# R² por modelo
ax1 = axes[0]
nombres_modelos = list(resultados.keys())
r2_scores = [resultados[n]['r2_test'] for n in nombres_modelos]
colors_bar = ['green' if n == mejor_nombre else 'skyblue' for n in nombres_modelos]
ax1.barh(nombres_modelos, r2_scores, color=colors_bar, edgecolor='black')
ax1.set_xlabel('R² Score', fontweight='bold')
ax1.set_title('Comparación de R² por Modelo', fontweight='bold')
ax1.grid(True, alpha=0.3, axis='x')
ax1.set_xlim(0, 1)

# MAE por modelo
ax2 = axes[1]
mae_scores = [resultados[n]['mae_test'] for n in nombres_modelos]
ax2.barh(nombres_modelos, mae_scores, color=colors_bar, edgecolor='black')
ax2.set_xlabel('MAE (kg)', fontweight='bold')
ax2.set_title('Comparación de MAE por Modelo', fontweight='bold')
ax2.grid(True, alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig(BASE_DIR / 'comparacion_modelos.png', dpi=300, bbox_inches='tight')
print(f"✓ Gráfico de comparación guardado en: {BASE_DIR / 'comparacion_modelos.png'}")

print(f"\n{'='*50}")
print(f" Entrenamiento completado exitosamente")
print(f"✓ Modelo seleccionado: {mejor_nombre}")
print(f"✓ R² Score: {mejores_metricas['r2_test']:.4f}")
print(f"{'='*50}")

plt.show()
