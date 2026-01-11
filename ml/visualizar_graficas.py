#!/usr/bin/env python3
"""
Script para generar y visualizar automáticamente todas las gráficas
de los estadísticos del dataset de despachos.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path de Python
sys.path.insert(0, str(Path(__file__).parent.parent))

from estadisticas import MLdatos, calculate_statistics, plot_statistics


def main():
    
    # Cargar datos
    df = MLdatos()
    
    if df is None:
        print("Error: No se pudieron cargar los datos")
        return
    
    print(f" Datos cargados: {len(df)} registros")
    print("\n Calculando estadísticos")
    
    # Calcular estadísticos
    stats = calculate_statistics(df)
    

    # Mostrar gráficas
    plot_statistics(stats)
    print("Proceso completado exitosamente")

if __name__ == "__main__":
    main()
