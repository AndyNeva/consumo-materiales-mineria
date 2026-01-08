#!/usr/bin/env python3
"""
Ejemplo de uso del módulo de estadísticas y visualización.
Este script demuestra cómo generar gráficas y guardarlas en archivos.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path de Python
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use('Agg')  # Backend sin ventanas emergentes (guarda archivos)

import matplotlib.pyplot as plt
import seaborn as sns
from ml.estadisticas import MLdatos, calculate_statistics

# Configurar estilo
sns.set_style("whitegrid")


def guardar_graficas(stats, output_dir='ml/graficas'):
    """Guarda todas las gráficas como archivos PNG"""
    
    # Crear directorio de salida
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"Guardando gráficas en: {output_dir}/")
    
    # 1. Volumen promedio por zona
    plt.figure(figsize=(14, 6))
    top_zonas = stats['volumen_promedio_por_zona'].nlargest(15)
    plt.bar(range(len(top_zonas)), top_zonas.values, color='steelblue', alpha=0.7)
    plt.xticks(range(len(top_zonas)), top_zonas.index, rotation=45, ha='right')
    plt.xlabel('Zona')
    plt.ylabel('Volumen Promedio (m³)')
    plt.title('Top 15 Zonas por Volumen Promedio de Despacho')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/01_volumen_por_zona.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  01_volumen_por_zona.png")
    
    # 2. Despachos por turno
    plt.figure(figsize=(8, 8))
    colors = ['#ff9999', '#66b3ff', '#99ff99']
    stats['despachos_por_turno'].plot(kind='pie', autopct='%1.1f%%', colors=colors, startangle=90)
    plt.ylabel('')
    plt.title('Distribución de Despachos por Turno')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/02_despachos_por_turno.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  02_despachos_por_turno.png")
    
    # 3. Asentamiento por fuente de cemento
    plt.figure(figsize=(10, 6))
    stats['asentamiento_por_cemento'].plot(kind='bar', color='coral', alpha=0.7)
    plt.xlabel('Fuente de Cemento')
    plt.ylabel('Asentamiento Promedio (cm)')
    plt.title('Asentamiento Promedio por Fuente de Cemento')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/03_asentamiento_por_cemento.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  03_asentamiento_por_cemento.png")
    
    # 4. Humedad de arena por zona
    plt.figure(figsize=(10, 8))
    top_humedad = stats['humedad_arena_por_zona'].nlargest(20)
    plt.barh(range(len(top_humedad)), top_humedad.values, color='lightgreen', alpha=0.7)
    plt.yticks(range(len(top_humedad)), top_humedad.index)
    plt.xlabel('Humedad Promedio (%)')
    plt.ylabel('Zona')
    plt.title('Top 20 Zonas por Humedad de Arena Promedio')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/04_humedad_arena.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  04_humedad_arena.png")
    
    # 5. Temperatura por turno
    plt.figure(figsize=(10, 6))
    stats['temperatura_por_turno'].plot(kind='bar', color='orange', alpha=0.7)
    plt.xlabel('Turno')
    plt.ylabel('Temperatura Promedio (°C)')
    plt.title('Temperatura Promedio por Turno')
    plt.xticks(rotation=45)
    plt.axhline(y=stats['temperatura_por_turno'].mean(), color='r', linestyle='--', 
                label=f'Media: {stats["temperatura_por_turno"].mean():.2f}°C')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{output_dir}/05_temperatura_por_turno.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  05_temperatura_por_turno.png")
    
    # 6. Despachos por lote
    plt.figure(figsize=(12, 6))
    top_lotes = stats['despachos_por_lote'].head(10)
    plt.bar(range(len(top_lotes)), top_lotes.values, color='purple', alpha=0.7)
    plt.xticks(range(len(top_lotes)), top_lotes.index, rotation=45, ha='right')
    plt.xlabel('Lote')
    plt.ylabel('Cantidad de Despachos')
    plt.title('Top 10 Lotes por Cantidad de Despachos')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/06_despachos_por_lote.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  06_despachos_por_lote.png")
    
    # 7. Volumen total por diseño
    plt.figure(figsize=(12, 8))
    top_disenos = stats['volumen_total_por_diseno'].nlargest(15)
    plt.barh(range(len(top_disenos)), top_disenos.values, color='teal', alpha=0.7)
    plt.yticks(range(len(top_disenos)), top_disenos.index)
    plt.xlabel('Volumen Total (m³)')
    plt.ylabel('Diseño de Mezcla')
    plt.title('Top 15 Diseños de Mezcla por Volumen Total')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/07_volumen_por_diseno.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  07_volumen_por_diseno.png")
    
    # 8. Asentamiento por diseño
    plt.figure(figsize=(14, 6))
    top_asentamiento = stats['asentamiento_por_diseno'].nlargest(15)
    plt.bar(range(len(top_asentamiento)), top_asentamiento.values, color='salmon', alpha=0.7)
    plt.xticks(range(len(top_asentamiento)), top_asentamiento.index, rotation=45, ha='right')
    plt.xlabel('Diseño de Mezcla')
    plt.ylabel('Asentamiento Promedio (cm)')
    plt.title('Top 15 Diseños de Mezcla por Asentamiento Promedio')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/08_asentamiento_por_diseno.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  08_asentamiento_por_diseno.png")
    
    # 9. Despachos por WBS
    plt.figure(figsize=(12, 6))
    top_wbs = stats['despachos_por_wbs'].head(10)
    plt.bar(range(len(top_wbs)), top_wbs.values, color='navy', alpha=0.7)
    plt.xticks(range(len(top_wbs)), top_wbs.index, rotation=45, ha='right')
    plt.xlabel('WBS')
    plt.ylabel('Cantidad de Despachos')
    plt.title('Top 10 WBS por Cantidad de Despachos')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/09_despachos_por_wbs.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  09_despachos_por_wbs.png")
    
    # 10. Correlación
    fig, ax = plt.subplots(figsize=(8, 6))
    corr_value = stats['correlacion_volumen_asentamiento']
    
    if abs(corr_value) < 0.3:
        color = 'gray'
        descripcion = 'Correlación Débil'
    elif abs(corr_value) < 0.7:
        color = 'orange'
        descripcion = 'Correlación Moderada'
    else:
        color = 'green'
        descripcion = 'Correlación Fuerte'
    
    ax.text(0.5, 0.6, f'{corr_value:.4f}', 
            ha='center', va='center', fontsize=80, color=color, weight='bold')
    ax.text(0.5, 0.3, descripcion, 
            ha='center', va='center', fontsize=20, color=color)
    ax.text(0.5, 0.15, 'Correlación entre Volumen y Asentamiento', 
            ha='center', va='center', fontsize=14, style='italic')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    plt.title('Correlación Volumen (m³) vs Asentamiento (cm)', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/10_correlacion.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  10_correlacion.png")
    
    print(f"\nTodas las gráficas guardadas en: {output_dir}/")


def main():
    """Función principal"""

    # Cargar datos
    print("\n Cargando datos...")
    df = MLdatos()
    
    if df is None:
        print(" Error: No se pudieron cargar los datos")
        return
    
    print(f"Datos cargados: {len(df)} registros")
    
    # Calcular estadísticos
    print("\nCalculando estadísticos...")
    stats = calculate_statistics(df)
    print(f" {len(stats)} estadísticos calculados")
    
    # Guardar gráficas
    print("\n Exportando gráficas a archivos PNG...")
    guardar_graficas(stats)

    print("PROCESO COMPLETADO")



if __name__ == "__main__":
    main()
