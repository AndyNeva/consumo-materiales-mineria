#!/usr/bin/env python3
"""
PLANIFICADOR DE PEDIDOS SEGÚN DEMANDA
------------------------------------
Este script calcula el consumo esperado de materias primas
a partir de la demanda proyectada (forecast diario)
y una receta promedio por m³.

Resultado:
- Consumo total por material
- Comparación con stock actual
- Pedido sugerido para cubrir un rango de días
"""

import os
import sqlite3
import pandas as pd

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

# Días a cubrir (puede cambiarse)
DIAS_A_CUBRIR = 20   # por ejemplo: resto de diciembre

# --------------------------------------------------
# CARGA DE FORECAST DIARIO
# --------------------------------------------------
def cargar_forecast_diario():
    """
    Carga la demanda diaria proyectada.
    Se asume que daily_demand contiene la demanda estimada.
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
# CARGA DE RECETA PROMEDIO
# --------------------------------------------------
def cargar_receta_promedio():
    """
    Calcula la receta promedio desde la tabla recetas,
    usando solo diseños válidos.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM recetas", conn)
    conn.close()

    df = df.fillna(0)

    # Filtrar recetas completas
    df = df[
        (df['cemento_kg'] > 0) &
        (df['arena_kg'] > 0) &
        (df['grava_kg'] > 0) &
        (df['agua_kg'] > 0)
    ]

    receta = df[[
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
    ]].mean()

    return receta


# --------------------------------------------------
# CARGA DE STOCK ACTUAL
# --------------------------------------------------
def cargar_stock_actual():
    """
    Carga el stock actual desde la tabla materiales.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT nombre, stock_actual
        FROM materiales
    """, conn)
    conn.close()

    return df.set_index('nombre')['stock_actual']


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("=== PLANIFICADOR DE PEDIDOS POR DEMANDA ===")

    # 1. Forecast diario
    df_forecast = cargar_forecast_diario()

    # Tomar solo los próximos N días
    df_rango = df_forecast.head(DIAS_A_CUBRIR)
    produccion_total = df_rango['volume_m3'].sum()

    print(f"\nProducción estimada para {DIAS_A_CUBRIR} días: {produccion_total:.2f} m³")

    # 2. Receta promedio
    receta = cargar_receta_promedio()

    # 3. Consumo total por material
    consumo = receta * produccion_total

    print("\n--- CONSUMO TOTAL ESTIMADO ---")
    for mat, val in consumo.items():
        print(f"{mat:30s}: {val:10.2f}")

    # 4. Stock actual
    stock = cargar_stock_actual()

    print("\n--- COMPARACIÓN CON STOCK ---")
    pedidos = {}

    for material in consumo.index:
        nombre_material = material.split('_')[0].capitalize()

        stock_disp = stock.get(nombre_material, 0)
        requerido = consumo[material]

        deficit = max(0, requerido - stock_disp)
        pedidos[nombre_material] = deficit

        print(
            f"{nombre_material:10s} | "
            f"Stock: {stock_disp:10.2f} | "
            f"Requerido: {requerido:10.2f} | "
            f"Pedido: {deficit:10.2f}"
        )

    print("\nPlanificación de pedidos completada correctamente.")


if __name__ == "__main__":
    main()
