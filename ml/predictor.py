"""
Módulo para realizar predicciones de materiales usando el modelo entrenado.
"""
import pickle
from pathlib import Path
import pandas as pd
import numpy as np


# Ruta al modelo guardado
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / 'modelo_prediccion_materiales.pkl'

# Cache del modelo cargado
_modelo_cache = None


def cargar_modelo():
    """Carga el modelo de predicción desde el archivo pickle.
    Usa caché para evitar cargar múltiples veces.
    
    Returns:
        dict: Diccionario con el modelo y sus metadatos
    """
    global _modelo_cache
    
    if _modelo_cache is not None:
        return _modelo_cache
    
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el modelo en {MODEL_PATH}. "
            "Ejecuta primero ml/MLPFuture.py para entrenar el modelo."
        )
    
    with open(MODEL_PATH, 'rb') as file:
        _modelo_cache = pickle.load(file)
    
    return _modelo_cache


def predecir_materiales(fecha_str, turno=None, diseno='OTROS', volumen=0):
    """Predice las cantidades de materiales necesarios para una fecha futura.
    
    Args:
        fecha_str (str): Fecha en formato 'YYYY-MM-DD'
        turno (str): 'DIA', 'NOCHE' o None (si None, calcula ambos turnos y suma)
        diseno (str): Nombre del diseño de mezcla
        volumen (float): Volumen en m³
        
    Returns:
        dict: Predicción con fecha y cantidades de Arena, Grava, Cemento
              Si turno=None, retorna suma de ambos turnos con desglose
        
    Raises:
        ValueError: Si los parámetros son inválidos
        FileNotFoundError: Si el modelo no existe
    """
    # Si turno es None, calcular ambos turnos y sumar
    if turno is None or str(turno).upper() == 'AMBOS':
        pred_dia = predecir_materiales(fecha_str, 'DIA', diseno, volumen)
        pred_noche = predecir_materiales(fecha_str, 'NOCHE', diseno, volumen)
        
        return {
            'fecha': fecha_str,
            'turno': 'AMBOS',
            'diseno': pred_dia['diseno'],
            'volumen_m3': float(volumen),
            'prediccion': {
                'arena_kg': round(pred_dia['prediccion']['arena_kg'] + pred_noche['prediccion']['arena_kg'], 2),
                'grava_kg': round(pred_dia['prediccion']['grava_kg'] + pred_noche['prediccion']['grava_kg'], 2),
                'cemento_kg': round(pred_dia['prediccion']['cemento_kg'] + pred_noche['prediccion']['cemento_kg'], 2)
            },
            'desglose': {
                'dia': pred_dia['prediccion'],
                'noche': pred_noche['prediccion']
            }
        }
    
    try:
        # Cargar modelo
        modelo_data = cargar_modelo()
        
        modelo = modelo_data['model']
        scaler_X = modelo_data['scaler_X']
        scaler_y = modelo_data['scaler_y']
        top_diseno = modelo_data['top_diseno']
        dummies_cols = modelo_data['dummies_cols']
        fecha_min = modelo_data['fecha_min']
        
        # Validar y parsear fecha
        try:
            fecha_prediccion = pd.to_datetime(fecha_str)
        except Exception as e:
            raise ValueError(f"Formato de fecha inválido: {fecha_str}. Usa 'YYYY-MM-DD'")
        
        # Calcular features temporales
        dias_desde_inicio = (fecha_prediccion - fecha_min).days
        mes = fecha_prediccion.month
        dia_anio = fecha_prediccion.dayofyear
        semana_anio = fecha_prediccion.isocalendar().week
        anio = fecha_prediccion.year
        
        # Turno
        turno_bin = str(turno).upper() == 'DIA'
        
        # Diseño
        diseno_mapeado = diseno if diseno in top_diseno else 'OTROS'
        dummies_input = {col: 0 for col in dummies_cols}
        col_name = f"DISENO_{diseno_mapeado}"
        if col_name in dummies_input:
            dummies_input[col_name] = 1
        
        # Construir features
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
            float(volumen)
        ]
        
        entrada_list = base_features + [dummies_input[col] for col in dummies_cols]
        entrada = np.array([entrada_list])
        
        # Predecir
        entrada_escalada = scaler_X.transform(entrada)
        prediccion_escalada = modelo.predict(entrada_escalada)
        prediccion = scaler_y.inverse_transform(prediccion_escalada)[0]
        
        # No permitir valores negativos
        prediccion = np.maximum(prediccion, 0)
        
        return {
            'fecha': fecha_str,
            'turno': turno.upper(),
            'diseno': diseno_mapeado,
            'volumen_m3': float(volumen),
            'prediccion': {
                'arena_kg': round(float(prediccion[0]), 2),
                'grava_kg': round(float(prediccion[1]), 2),
                'cemento_kg': round(float(prediccion[2]), 2)
            }
        }
        
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Error al realizar la predicción: {str(e)}")


def obtener_info_modelo():
    """Obtiene información sobre el modelo cargado.
    
    Returns:
        dict: Información del modelo (nombre, métricas, fechas, diseños)
    """
    try:
        modelo_data = cargar_modelo()
        
        return {
            'modelo': modelo_data['model_name'],
            'features': modelo_data['features'],
            'targets': modelo_data['targets'],
            'disenos_disponibles': modelo_data['top_diseno'] + ['OTROS'],
            'fecha_min_entrenamiento': str(modelo_data['fecha_min']),
            'fecha_max_entrenamiento': str(modelo_data['fecha_max']),
            'metricas': modelo_data['metricas']
        }
    except Exception as e:
        raise Exception(f"Error al obtener información del modelo: {str(e)}")


def predecir_batch(predicciones_lista):
    """Realiza múltiples predicciones en batch.
    
    Args:
        predicciones_lista (list): Lista de diccionarios con parámetros de predicción
        
    Returns:
        list: Lista de resultados de predicción
    """
    resultados = []
    errores = []
    
    for i, params in enumerate(predicciones_lista):
        try:
            resultado = predecir_materiales(
                fecha_str=params.get('fecha'),
                turno=params.get('turno', 'DIA'),
                diseno=params.get('diseno', 'OTROS'),
                volumen=params.get('volumen', 6.0)
            )
            resultados.append(resultado)
        except Exception as e:
            errores.append({
                'indice': i,
                'parametros': params,
                'error': str(e)
            })
    
    return {
        'predicciones': resultados,
        'errores': errores,
        'total_exitosas': len(resultados),
        'total_errores': len(errores)
    }


if __name__ == "__main__":
    # Test del módulo
    print("=== Test del Módulo de Predicción ===\n")
    
    # 1. Info del modelo
    try:
        info = obtener_info_modelo()
        print("✓ Información del modelo:")
        print(f"  Modelo: {info['modelo']}")
        print(f"  Diseños: {', '.join(info['disenos_disponibles'][:5])}...")
        print(f"  R² global: {info['metricas']['r2_global']:.4f}")
        print()
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    # 2. Predicción simple
    try:
        prediccion = predecir_materiales(
            fecha_str='2026-03-15',
            turno='DIA',
            diseno='H25',
            volumen=8.0
        )
        print("✓ Predicción individual:")
        print(f"  Fecha: {prediccion['fecha']}")
        print(f"  Arena: {prediccion['prediccion']['arena_kg']:,.2f} kg")
        print(f"  Grava: {prediccion['prediccion']['grava_kg']:,.2f} kg")
        print(f"  Cemento: {prediccion['prediccion']['cemento_kg']:,.2f} kg")
        print()
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    # 3. Predicción batch
    try:
        batch = [
            {'fecha': '2026-04-01', 'turno': 'DIA', 'diseno': 'H25', 'volumen': 6},
            {'fecha': '2026-04-02', 'turno': 'NOCHE', 'diseno': 'H30', 'volumen': 8},
        ]
        resultado_batch = predecir_batch(batch)
        print(f"✓ Predicción batch: {resultado_batch['total_exitosas']} exitosas")
    except Exception as e:
        print(f"✗ Error: {e}")
