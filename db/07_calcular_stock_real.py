#!/usr/bin/env python3
"""
CÁLCULO DE STOCK REAL
--------------------
Calcula el stock actual de cada material
a partir de los movimientos de ingreso y egreso.
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
# FUNCIÓN PRINCIPAL
# --------------------------------------------------
def calcular_stock_real():
    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql("""
        SELECT
            m.id AS material_id,
            m.nombre AS material,
            SUM(
                CASE
                    WHEN mov.tipo = 'INGRESO' THEN mov.cantidad
                    WHEN mov.tipo = 'EGRESO' THEN -mov.cantidad
                    ELSE 0
                END
            ) AS stock_real
        FROM movimientos mov
        JOIN materiales m ON m.id = mov.material_id
        GROUP BY m.id, m.nombre
    """, conn)

    conn.close()
    return df


# --------------------------------------------------
# EJECUCIÓN DIRECTA
# --------------------------------------------------
if __name__ == "__main__":
    print("=== STOCK REAL CALCULADO DESDE MOVIMIENTOS ===")
    stock = calcular_stock_real()
    print(stock)
