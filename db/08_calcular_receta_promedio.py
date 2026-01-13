#!/usr/bin/env python3
"""
CÁLCULO DE RECETA PROMEDIO
--------------------------
Este script calcula una receta promedio de concreto
a partir de los diseños almacenados en la tabla `recetas`.

Objetivo:
- Obtener una receta representativa (kg por m³)
- Excluir diseños incompletos o atípicos
- Usar esta receta para planificación de materiales
"""

import sqlite3
import pandas as pd
import os

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
def cargar_recetas():
    """
    Carga la tabla recetas desde SQLite
    y la devuelve como DataFrame.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT *
        FROM recetas
    """, conn)
    conn.close()
    return df


# --------------------------------------------------
# FILTRADO DE RECETAS VÁLIDAS
# --------------------------------------------------
def filtrar_recetas_validas(df):
    """
    Filtra únicamente recetas completas y válidas.

    Criterios:
    - Cemento > 0
    - Arena > 0
    - Grava > 0
    - Agua > 0

    Los aditivos vacíos se consideran 0.
    """

    df = df.copy()

    # Reemplazar valores nulos por 0 (principalmente aditivos)
    df = df.fillna(0)

    # Aplicar filtros de recetas completas
    df_validas = df[
        (df['cemento_kg'] > 0) &
        (df['arena_kg'] > 0) &
        (df['grava_kg'] > 0) &
        (df['agua_kg'] > 0)
    ]

    return df_validas


# --------------------------------------------------
# CÁLCULO DE RECETA PROMEDIO
# --------------------------------------------------
def calcular_receta_promedio(df):
    """
    Calcula el promedio por columna
    (kg o litros por m³).
    """

    columnas_materiales = [
        'cemento_kg',
        'arena_kg',
        'grava_kg',
        'agua_kg',
        'aditivo_a',
        'aditivo_b',
        'aditivo_delvo',
        'aditivo_glenium_7950',
        'aditivo_glenium_7970',
        'aditivo_fibras'
    ]

    receta_promedio = df[columnas_materiales].mean()

    return receta_promedio


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== CÁLCULO DE RECETA PROMEDIO ===")

    # 1. Cargar recetas
    df_recetas = cargar_recetas()
    print(f"Recetas totales cargadas: {len(df_recetas)}")

    # 2. Filtrar recetas válidas
    df_validas = filtrar_recetas_validas(df_recetas)
    print(f"Recetas válidas para promedio: {len(df_validas)}")

    if df_validas.empty:
        print("No hay recetas válidas para calcular promedio.")
        return

    # 3. Calcular receta promedio
    receta_promedio = calcular_receta_promedio(df_validas)

    print("\n--- RECETA PROMEDIO (kg por m³) ---")
    for material, valor in receta_promedio.items():
        print(f"{material:30s}: {valor:8.2f}")

    print("\nLa receta promedio está lista para planificación.")


if __name__ == "__main__":
    main()
