<<<<<<< Updated upstream
import sys
from pathlib import Path

# Agregar el directorio raíz al path de Python
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from utils.loaders import cargar_datos_tabla

# Configurar estilo de gráficos
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

def MLdatos():
    """Carga el dataset de despachos desde la base de datos y lo devuelve como DataFrame"""
    try:
        datos = cargar_datos_tabla("despachos")
        df = pd.DataFrame(datos)
        return df
    except Exception as e:
        print(f"Error al cargar los datos: {e}")
        return None


def calculate_statistics(df):
    """Calcula 10 estadísticos graficables del dataset"""
    stats = {}
    
    # 1. Promedio de volumen por zona
    stats['volumen_promedio_por_zona'] = df.groupby('zona')['volumen_m3'].mean()
    
    # 2. Cantidad de despachos por turno
    stats['despachos_por_turno'] = df['turno'].value_counts()
    
    # 3. Asentamiento promedio por fuente de cemento
    stats['asentamiento_por_cemento'] = df.groupby('fuente_cemento')['asentamiento_final_cm'].mean()
    
    # 4. Humedad de arena promedio por zona
    stats['humedad_arena_por_zona'] = df.groupby('zona')['arena_humedad_pct'].mean()
    
    # 5. Temperatura promedio por turno
    stats['temperatura_por_turno'] = df.groupby('turno')['temperatura_c'].mean()
    
    # 6. Despachos por lote
    stats['despachos_por_lote'] = df['lote'].value_counts()
    
    # 7. Volumen total por diseño de mezcla
    stats['volumen_total_por_diseno'] = df.groupby('diseno_mezcla')['volumen_m3'].sum()
    
    # 8. Asentamiento por diseño de mezcla
    stats['asentamiento_por_diseno'] = df.groupby('diseno_mezcla')['asentamiento_final_cm'].mean()
    
    # 9. Despachos por WBS
    stats['despachos_por_wbs'] = df['wbs'].value_counts()
    
    # 10. Correlación entre volumen y asentamiento
    stats['correlacion_volumen_asentamiento'] = df['volumen_m3'].corr(df['asentamiento_final_cm'])
    
    return stats


def plot_statistics(stats):
    """Genera gráficos en ventanas emergentes para cada estadístico"""
    
    # 1. Gráfico de barras: Volumen promedio por zona (Top 15)
    plt.figure(figsize=(14, 6))
    top_zonas = stats['volumen_promedio_por_zona'].nlargest(15)
    plt.bar(range(len(top_zonas)), top_zonas.values, color='steelblue', alpha=0.7)
    plt.xticks(range(len(top_zonas)), top_zonas.index, rotation=45, ha='right')
    plt.xlabel('Zona')
    plt.ylabel('Volumen Promedio (m³)')
    plt.title('Top 15 Zonas por Volumen Promedio de Despacho')
    plt.tight_layout()
    plt.show()
    
    # 2. Gráfico de pastel: Despachos por turno
    plt.figure(figsize=(8, 8))
    colors = ["#c15ed2", "#336393", "#64cd64"]
    stats['despachos_por_turno'].plot(kind='pie', autopct='%1.1f%%', colors=colors, startangle=90)
    plt.ylabel('')
    plt.title('Distribución de Despachos por Turno')
    plt.tight_layout()
    plt.show()
    
    # 3. Gráfico de barras: Asentamiento promedio por fuente de cemento
    plt.figure(figsize=(10, 6))
    stats['asentamiento_por_cemento'].plot(kind='bar', color='coral', alpha=0.7)
    plt.xlabel('Fuente de Cemento')
    plt.ylabel('Asentamiento Promedio (cm)')
    plt.title('Asentamiento Promedio por Fuente de Cemento')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.show()
    
    # 4. Gráfico de barras horizontales: Humedad de arena por zona (Top 20)
    plt.figure(figsize=(10, 8))
    top_humedad = stats['humedad_arena_por_zona'].nlargest(20)
    plt.barh(range(len(top_humedad)), top_humedad.values, color='lightgreen', alpha=0.7)
    plt.yticks(range(len(top_humedad)), top_humedad.index)
    plt.xlabel('Humedad Promedio (%)')
    plt.ylabel('Zona')
    plt.title('Top 20 Zonas por Humedad de Arena Promedio')
    plt.tight_layout()
    plt.show()
    
    # 5. Gráfico de barras: Temperatura promedio por turno
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
    plt.show()
    
    # 6. Gráfico de barras: Despachos por lote (Top 10)
    plt.figure(figsize=(12, 6))
    top_lotes = stats['despachos_por_lote'].head(10)
    plt.bar(range(len(top_lotes)), top_lotes.values, color='purple', alpha=0.7)
    plt.xticks(range(len(top_lotes)), top_lotes.index, rotation=45, ha='right')
    plt.xlabel('Lote')
    plt.ylabel('Cantidad de Despachos')
    plt.title('Top 10 Lotes por Cantidad de Despachos')
    plt.tight_layout()
    plt.show()
    
    # 7. Gráfico de barras horizontales: Volumen total por diseño de mezcla (Top 15)
    plt.figure(figsize=(12, 8))
    top_disenos = stats['volumen_total_por_diseno'].nlargest(15)
    plt.barh(range(len(top_disenos)), top_disenos.values, color='teal', alpha=0.7)
    plt.yticks(range(len(top_disenos)), top_disenos.index)
    plt.xlabel('Volumen Total (m³)')
    plt.ylabel('Diseño de Mezcla')
    plt.title('Top 15 Diseños de Mezcla por Volumen Total')
    plt.tight_layout()
    plt.show()
    
    # 8. Gráfico de barras: Asentamiento por diseño de mezcla (Top 15)
    plt.figure(figsize=(14, 6))
    top_asentamiento = stats['asentamiento_por_diseno'].nlargest(15)
    plt.bar(range(len(top_asentamiento)), top_asentamiento.values, color='salmon', alpha=0.7)
    plt.xticks(range(len(top_asentamiento)), top_asentamiento.index, rotation=45, ha='right')
    plt.xlabel('Diseño de Mezcla')
    plt.ylabel('Asentamiento Promedio (cm)')
    plt.title('Top 15 Diseños de Mezcla por Asentamiento Promedio')
    plt.tight_layout()
    plt.show()
    
    # 9. Gráfico de barras: Despachos por WBS (Top 10)
    plt.figure(figsize=(12, 6))
    top_wbs = stats['despachos_por_wbs'].head(10)
    plt.bar(range(len(top_wbs)), top_wbs.values, color='navy', alpha=0.7)
    plt.xticks(range(len(top_wbs)), top_wbs.index, rotation=45, ha='right')
    plt.xlabel('WBS')
    plt.ylabel('Cantidad de Despachos')
    plt.title('Top 10 WBS por Cantidad de Despachos')
    plt.tight_layout()
    plt.show()
    
    # 10. Gráfico de texto: Correlación volumen-asentamiento
    fig, ax = plt.figure(figsize=(8, 6)), plt.gca()
    corr_value = stats['correlacion_volumen_asentamiento']
    
    # Determinar color y descripción basado en el valor de correlación
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
    plt.show()
    
    print("\n Todas las gráficas han sido generadas y mostradas")


if __name__ == "__main__":
    df = MLdatos()
    if df is not None:
        print("Primeras filas del dataset:")
        print(df.head())
        print("\nInformación del dataset:")
        print(df.info())
        print("\nEstadísticas descriptivas:")
        print(df.describe())
        
        print("\n" + "="*50)
        print("ESTADÍSTICOS CALCULADOS")
        print("="*50)
        
        stats = calculate_statistics(df)
        for nombre, valor in stats.items():
            print(f"\n{nombre}:")
            print(valor)
        
        # Preguntar si desea ver las gráficas
        respuesta = input("¿Desea ver las gráficas en ventanas emergentes? (s/n): ").strip().lower()
        if respuesta in ['s', 'si', 'sí', 'yes', 'y']:
            print("\n Generando gráficas...")
            plot_statistics(stats)
=======
import pandas as pd

from utils.loaders import get_db_connection_standalone

def MLdatos():
    conn = None
    try:
        conn = get_db_connection_standalone()
        cursor = conn.execute(
            """
            SELECT
                fecha,
                fuente_cemento,
                diseno_mezcla,
                lote,
                zona,
                wbs,
                volumen_m3,
                turno,
                arena_humedad_pct,
                asentamiento_final_cm,
                temperatura_c
            FROM despachos
            """
        )

        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return pd.DataFrame(rows, columns=columns)
    except Exception as e:
        print(f"Error al obtener datos: {e}")
        return None
    finally:
        if conn:
            conn.close()
            
            df = MLdatos()
            if df is not None:
                print("Primeras filas del dataset:")
                print(df.head())
                print("\nInformación del dataset:")
                print(df.info())
                print("\nEstadísticas descriptivas:")
                print(df.describe())

                
>>>>>>> Stashed changes
