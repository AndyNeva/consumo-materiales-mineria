#!/usr/bin/env python3
"""
COMPARACIÓN FINAL DE MODELOS DE DEMANDA
--------------------------------------
Genera una tabla comparativa y dos gráficas
(MAE y R²) con etiquetas visibles en cada barra.
"""

import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------
# RESULTADOS DE LOS MODELOS (AJUSTA SI ES NECESARIO)
# --------------------------------------------------
data = [
    {
        "Modelo": "Promedio móvil (datos limpios)",
        "MAE": 7.72,
        "RMSE": 10.34,
        "R2": 0.38
    },
    {
        "Modelo": "Promedio móvil (original)",
        "MAE": 8.83,
        "RMSE": 13.71,
        "R2": 0.30
    },
    {
        "Modelo": "Random Forest",
        "MAE": 8.90,
        "RMSE": 11.80,
        "R2": 0.15
    },
    {
        "Modelo": "Regresión lineal",
        "MAE": 9.90,
        "RMSE": 12.65,
        "R2": 0.02
    }
]

df = pd.DataFrame(data).sort_values("MAE")

# --------------------------------------------------
# MOSTRAR TABLA
# --------------------------------------------------
print("\n=== COMPARACIÓN FINAL DE MODELOS ===")
print(df)

# --------------------------------------------------
# FUNCIÓN PARA ETIQUETAR BARRAS
# --------------------------------------------------
def etiquetar_barras(ax, valores, formato="{:.2f}"):
    """
    Agrega etiquetas numéricas al final de cada barra horizontal.
    """
    for i, v in enumerate(valores):
        ax.text(v, i, formato.format(v), va='center', ha='left', fontsize=10)

# --------------------------------------------------
# GRÁFICO 1: MAE
# --------------------------------------------------
plt.figure(figsize=(10, 5))
ax1 = plt.gca()
ax1.barh(df["Modelo"], df["MAE"])
ax1.set_xlabel("MAE (m³)")
ax1.set_title("Comparación de modelos – Error Absoluto Medio (MAE)")
ax1.invert_yaxis()

etiquetar_barras(ax1, df["MAE"])

plt.tight_layout()
plt.show()

# --------------------------------------------------
# GRÁFICO 2: R²
# --------------------------------------------------
plt.figure(figsize=(10, 5))
ax2 = plt.gca()
ax2.barh(df["Modelo"], df["R2"])
ax2.set_xlabel("R²")
ax2.set_title("Comparación de modelos – Coeficiente de Determinación (R²)")
ax2.invert_yaxis()

etiquetar_barras(ax2, df["R2"], formato="{:.3f}")

plt.tight_layout()
plt.show()

# --------------------------------------------------
# MODELO GANADOR
# --------------------------------------------------
print("\n=== MODELO RECOMENDADO ===")
print(df.iloc[0])

