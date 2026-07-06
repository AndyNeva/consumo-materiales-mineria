import pandas as pd


def limpiar_numero(valor):
    """Convierte valores del Excel a float, manejando casos especiales"""
    # Si es NaN
    if pd.isna(valor):
        return 0.0

    # Si ya es número, lo devuelve como float
    if isinstance(valor, (int, float)):
        return float(valor)

    # Limpieza básica de strings
    val_str = str(valor).strip()

    # Casos comunes de valores vacíos
    if val_str in ['-', '', 'nan', 'None']:
        return 0.0

    # Manejo de números negativos entre paréntesis (ej: (123))
    multiplicador = 1.0
    if '(' in val_str and ')' in val_str:
        multiplicador = -1.0
        val_str = val_str.replace('(', '').replace(')', '')

    try:
        # Reemplaza coma decimal si aplica
        if ',' in val_str and '.' not in val_str:
            val_str = val_str.replace(',', '.')
        return float(val_str) * multiplicador
    except ValueError:
        return 0.0
