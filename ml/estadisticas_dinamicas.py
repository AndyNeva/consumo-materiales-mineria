"""
Módulo para generar gráficas estadísticas dinámicas basadas en datos filtrados.
Este módulo genera gráficas apropiadas según la cantidad de datos disponibles.
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import json


# Definición de columnas
MATERIALES_COLS = ['Arena (kg)', 'Grava (kg)', 'Cemento (kg)', 'Agua (kg)']
ADITIVOS_COLS = [
    'RHEO 1000 (kg)',
    'BASF 719 (kg)',
    'Delvo (litros)',
    'MasterGlenium 7950',
    'MasterGlenium 7970',
    'Sika PP 48 (kg)-BARCHIP',
]


def _fig_to_obj(fig) -> dict:
    """Convierte figura Plotly a objeto dict (data+layout) con serialización completa."""
    import json
    # Usar PlotlyJSONEncoder para convertir correctamente numpy arrays
    fig_dict = fig.to_plotly_json()
    # Re-serializar y deserializar para convertir todos los numpy arrays a listas nativas
    json_str = json.dumps(fig_dict, cls=PlotlyJSONEncoder)
    return json.loads(json_str)


def validar_columnas_dataframe(df: pd.DataFrame) -> tuple[list, list]:
    """Valida qué columnas de materiales y aditivos existen en el DataFrame.
    
    Returns:
        tuple: (columnas_materiales_presentes, columnas_aditivos_presentes)
    """
    materiales_presentes = [c for c in MATERIALES_COLS if c in df.columns]
    aditivos_presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    return materiales_presentes, aditivos_presentes


def recomendar_graficas(num_registros: int) -> dict:
    """Recomienda qué gráficas usar según la cantidad de registros.
    
    Args:
        num_registros: Cantidad de registros en el dataset
        
    Returns:
        dict con recomendaciones y umbrales
    """
    recomendaciones = {
        'num_registros': num_registros,
        'graficas_recomendadas': [],
        'graficas_no_recomendadas': [],
        'advertencias': []
    }
    
    if num_registros == 0:
        recomendaciones['advertencias'].append('No hay datos para generar gráficas')
        return recomendaciones
    
    # Siempre útiles
    recomendaciones['graficas_recomendadas'].extend([
        'resumen_numerico',
        'estadisticos_aditivos'
    ])
    
    if num_registros >= 2:
        recomendaciones['graficas_recomendadas'].append('volumen_por_dia_mezcla')
    else:
        recomendaciones['graficas_no_recomendadas'].append('volumen_por_dia_mezcla')
        recomendaciones['advertencias'].append('Mínimo 2 registros para gráfico de volumen por día')
    
    if num_registros >= 5:
        recomendaciones['graficas_recomendadas'].append('frecuencia_disenos')
    else:
        recomendaciones['graficas_no_recomendadas'].append('frecuencia_disenos')
        recomendaciones['advertencias'].append('Muy pocos datos para gráfico de frecuencia')
    
    if num_registros >= 10:
        recomendaciones['graficas_recomendadas'].extend([
            'boxplot_materiales',
            'boxplot_aditivos'
        ])
    else:
        recomendaciones['graficas_no_recomendadas'].extend([
            'boxplot_materiales',
            'boxplot_aditivos'
        ])
        recomendaciones['advertencias'].append('Mínimo 10 registros recomendados para boxplots')
    
    if num_registros >= 30:
        recomendaciones['graficas_recomendadas'].append('histograma_aditivos')
    else:
        recomendaciones['graficas_no_recomendadas'].append('histograma_aditivos')
        recomendaciones['advertencias'].append('Mínimo 30 registros recomendados para histogramas')
    
    if num_registros >= 50:
        recomendaciones['graficas_recomendadas'].extend([
            'matriz_correlacion_materiales',
            'correlacion_aditivos'
        ])
    else:
        recomendaciones['graficas_no_recomendadas'].extend([
            'matriz_correlacion_materiales',
            'correlacion_aditivos'
        ])
        recomendaciones['advertencias'].append('Mínimo 50 registros recomendados para correlaciones confiables')
    
    return recomendaciones


def generar_graficas_desde_datos(df: pd.DataFrame) -> dict:
    """Genera todas las gráficas apropiadas basadas en los datos proporcionados.
    
    Args:
        df: DataFrame con los datos filtrados (debe tener columnas en español como vienen de la BD)
        
    Returns:
        dict con las gráficas generadas y metadatos
    """
    num_registros = len(df)
    recomendaciones = recomendar_graficas(num_registros)
    
    # Mapeo de columnas de BD a columnas de análisis
    mapeo_columnas = {
        'arena_kg': 'Arena (kg)',
        'grava_kg': 'Grava (kg)',
        'cemento_he_kg': 'Cemento HE (kg)',
        'cemento_ip_kg': 'Cemento IP (kg)',
        'agua_kg': 'Agua (kg)',
        'volumen_m3': 'Volumen (m3)',
        'diseno_mezcla': 'Diseño de la Mezcla',
        'aditivo_rheo_sika115': 'RHEO 1000 (kg)',
        'aditivo_basf_sika200': 'BASF 719 (kg)',
        'aditivo_delvo': 'Delvo (litros)',
        'aditivo_glenium_7950': 'MasterGlenium 7950',
        'aditivo_glenium_7970': 'MasterGlenium 7970',
        'aditivo_fibras': 'Sika PP 48 (kg)-BARCHIP',
    }
    
    # Renombrar columnas si vienen de la BD
    df_trabajo = df.copy()
    df_trabajo.rename(columns=mapeo_columnas, inplace=True)
    
    # Sumar cementos si existen ambos
    if 'Cemento HE (kg)' in df_trabajo.columns and 'Cemento IP (kg)' in df_trabajo.columns:
        df_trabajo['Cemento (kg)'] = df_trabajo['Cemento HE (kg)'].fillna(0) + df_trabajo['Cemento IP (kg)'].fillna(0)
    elif 'Cemento HE (kg)' in df_trabajo.columns:
        df_trabajo['Cemento (kg)'] = df_trabajo['Cemento HE (kg)']
    elif 'Cemento IP (kg)' in df_trabajo.columns:
        df_trabajo['Cemento (kg)'] = df_trabajo['Cemento IP (kg)']
    
    # Convertir a numérico
    materiales_presentes, aditivos_presentes = validar_columnas_dataframe(df_trabajo)
    columnas_numericas = materiales_presentes + aditivos_presentes + ['Volumen (m3)']
    columnas_numericas = [c for c in columnas_numericas if c in df_trabajo.columns]
    
    for col in columnas_numericas:
        df_trabajo[col] = pd.to_numeric(df_trabajo[col], errors='coerce')
    
    resultado = {
        'metadatos': {
            'num_registros': num_registros,
            'recomendaciones': recomendaciones,
            'fecha_generacion': pd.Timestamp.now().isoformat()
        },
        'graficas': {}
    }
    
    # Generar solo las gráficas recomendadas
    graficas_recomendadas = recomendaciones['graficas_recomendadas']
    
    # 1. Resumen numérico (siempre)
    if 'resumen_numerico' in graficas_recomendadas:
        fig_resumen = _generar_resumen_numerico(df_trabajo, materiales_presentes, aditivos_presentes)
        if fig_resumen:
            resultado['graficas']['resumen_numerico'] = fig_resumen
    
    # 2. Estadísticos aditivos (siempre)
    if 'estadisticos_aditivos' in graficas_recomendadas:
        fig_aditivos = _generar_estadisticos_aditivos(df_trabajo, aditivos_presentes)
        if fig_aditivos:
            resultado['graficas']['estadisticos_aditivos'] = fig_aditivos
    
    # 3. Volumen por día y mezcla (2+ registros)
    if 'volumen_por_dia_mezcla' in graficas_recomendadas:
        fig_volumen = _generar_volumen_por_dia_mezcla(df_trabajo)
        if fig_volumen:
            resultado['graficas']['volumen_por_dia_mezcla'] = fig_volumen
    
    # 5. Frecuencia de diseños (5+ registros)
    if 'frecuencia_disenos' in graficas_recomendadas and 'Diseño de la Mezcla' in df_trabajo.columns:
        fig_freq = _generar_frecuencia_disenos(df_trabajo)
        if fig_freq:
            resultado['graficas']['frecuencia_disenos'] = fig_freq
    
    # 4. Boxplots (10+ registros)
    if 'boxplot_materiales' in graficas_recomendadas:
        fig_box_mat = _generar_boxplot_materiales(df_trabajo, materiales_presentes)
        if fig_box_mat:
            resultado['graficas']['boxplot_materiales'] = fig_box_mat
    
    if 'boxplot_aditivos' in graficas_recomendadas:
        fig_box_adit = _generar_boxplot_aditivos(df_trabajo, aditivos_presentes)
        if fig_box_adit:
            resultado['graficas']['boxplot_aditivos'] = fig_box_adit
    
    # 6. Histograma (30+ registros)
    if 'histograma_aditivos' in graficas_recomendadas:
        fig_hist = _generar_histograma_aditivos(df_trabajo, aditivos_presentes)
        if fig_hist:
            resultado['graficas']['histograma_aditivos'] = fig_hist
    
    # 7. Correlaciones (50+ registros)
    if 'matriz_correlacion_materiales' in graficas_recomendadas:
        fig_corr_mat = _generar_matriz_correlacion(df_trabajo, materiales_presentes)
        if fig_corr_mat:
            resultado['graficas']['matriz_correlacion_materiales'] = fig_corr_mat
    
    if 'correlacion_aditivos' in graficas_recomendadas:
        fig_corr_adit = _generar_correlacion_aditivos(df_trabajo, aditivos_presentes)
        if fig_corr_adit:
            resultado['graficas']['correlacion_aditivos'] = fig_corr_adit
    
    return resultado


# ========== Funciones auxiliares para generar cada gráfica ==========

def _generar_resumen_numerico(df: pd.DataFrame, materiales: list, aditivos: list):
    """Genera tabla de resumen numérico."""
    columnas = materiales + aditivos
    columnas = [c for c in columnas if c in df.columns]
    if not columnas:
        return None
    
    resumen = df[columnas].describe()
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Estadístico'] + list(resumen.columns),
            fill_color='paleturquoise',
            align='left',
            font=dict(size=12, color='black')
        ),
        cells=dict(
            values=[resumen.index.tolist()] + [resumen[col].round(2).tolist() for col in resumen.columns],
            fill_color='lavender',
            align='left',
            font=dict(size=11)
        )
    )])
    fig.update_layout(title="Resumen Numérico - Materiales y Aditivos", height=500)
    return _fig_to_obj(fig)


def _generar_estadisticos_aditivos(df: pd.DataFrame, aditivos: list):
    """Genera tabla de estadísticos de aditivos."""
    aditivos = [c for c in aditivos if c in df.columns]
    if not aditivos:
        return None
    
    desc = df[aditivos].describe()
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Estadístico'] + list(desc.columns),
            fill_color='lightcoral',
            align='left',
            font=dict(size=12, color='black')
        ),
        cells=dict(
            values=[desc.index.tolist()] + [desc[col].round(2).tolist() for col in desc.columns],
            fill_color='mistyrose',
            align='left',
            font=dict(size=11)
        )
    )])
    fig.update_layout(title="Estadísticos Descriptivos - Aditivos", height=500)
    return _fig_to_obj(fig)


def _generar_volumen_por_dia_mezcla(df: pd.DataFrame):
    """Genera gráfico de volumen utilizado por día y por diseño de mezcla."""
    # Verificar columnas necesarias
    if 'Diseño de la Mezcla' not in df.columns or 'Volumen (m3)' not in df.columns:
        # Intentar con nombres de BD si no están las columnas renombradas
        if 'diseno_mezcla' in df.columns and 'volumen_m3' in df.columns:
            df = df.copy()
            df['Diseño de la Mezcla'] = df['diseno_mezcla']
            df['Volumen (m3)'] = df['volumen_m3']
        else:
            return None
    
    # Determinar columna de fecha
    fecha_col = None
    for col in ['fecha', 'FECHA', 'Fecha']:
        if col in df.columns:
            fecha_col = col
            break
    
    if not fecha_col:
        return None
    
    # Convertir fecha a datetime
    df_copy = df.copy()
    df_copy[fecha_col] = pd.to_datetime(df_copy[fecha_col])
    df_copy['Fecha'] = df_copy[fecha_col].dt.date
    
    # Agrupar por fecha y diseño
    agrupado = df_copy.groupby(['Fecha', 'Diseño de la Mezcla'])['Volumen (m3)'].sum().reset_index()
    
    # Crear gráfico de líneas con marcadores
    fig = px.line(agrupado, 
                  x='Fecha', 
                  y='Volumen (m3)', 
                  color='Diseño de la Mezcla',
                  title='Volumen Utilizado por Día y Diseño de Mezcla',
                  markers=True,
                  line_shape='linear')
    
    fig.update_layout(
        xaxis_title='Fecha',
        yaxis_title='Volumen (m³)',
        height=500,
        hovermode='x unified',
        legend=dict(
            title='Diseño de Mezcla',
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02
        )
    )
    
    fig.update_traces(mode='lines+markers')
    
    return _fig_to_obj(fig)


def _generar_frecuencia_disenos(df: pd.DataFrame):
    """Genera gráfico de frecuencia de diseños."""
    if 'Diseño de la Mezcla' not in df.columns:
        return None
    mix_counts = df['Diseño de la Mezcla'].value_counts().reset_index()
    mix_counts.columns = ['Diseño', 'Frecuencia']
    fig = px.bar(mix_counts, x='Diseño', y='Frecuencia', 
                 title='Frecuencia de Diseños de Mezcla',
                 color='Frecuencia',
                 color_continuous_scale='viridis')
    fig.update_layout(xaxis_tickangle=-45, height=500)
    return _fig_to_obj(fig)


def _generar_boxplot_materiales(df: pd.DataFrame, materiales: list):
    """Genera boxplot de materiales."""
    materiales = [c for c in materiales if c in df.columns]
    if not materiales:
        return None
    df_long = df[materiales].melt(var_name="Material", value_name="Cantidad")
    fig = px.box(df_long, x="Material", y="Cantidad", 
                 title="Distribución de Materiales",
                 color="Material")
    fig.update_layout(xaxis_tickangle=-45, height=500)
    return _fig_to_obj(fig)


def _generar_boxplot_aditivos(df: pd.DataFrame, aditivos: list):
    """Genera boxplot de aditivos."""
    aditivos = [c for c in aditivos if c in df.columns]
    if not aditivos:
        return None
    df_long = df[aditivos].melt(var_name="Aditivo", value_name="Cantidad")
    fig = px.box(df_long, x="Aditivo", y="Cantidad", 
                 title="Distribución de Aditivos",
                 color="Aditivo")
    fig.update_layout(xaxis_tickangle=-45, height=500)
    return _fig_to_obj(fig)


def _generar_histograma_aditivos(df: pd.DataFrame, aditivos: list):
    """Genera histograma superpuesto de aditivos."""
    aditivos = [c for c in aditivos if c in df.columns]
    if not aditivos:
        return None
    fig = go.Figure()
    for c in aditivos:
        serie = df[c].dropna().tolist()
        if len(serie) > 0:  # Solo agregar si hay datos
            fig.add_trace(go.Histogram(x=serie, name=c, opacity=0.6, nbinsx=20))
    fig.update_layout(
        barmode='overlay',
        title="Distribución de Aditivos",
        xaxis_title="Cantidad (kg o litros)",
        yaxis_title="Frecuencia",
        height=600
    )
    return _fig_to_obj(fig)


def _generar_matriz_correlacion(df: pd.DataFrame, materiales: list):
    """Genera matriz de correlación de materiales."""
    cols = materiales + ['Volumen (m3)']
    cols = [c for c in cols if c in df.columns]
    if len(cols) < 2:
        return None
    
    corr = df[cols].corr(numeric_only=True)
    fig = go.Figure(data=go.Heatmap(
        z=corr.values.tolist(),
        x=corr.columns.tolist(),
        y=corr.columns.tolist(),
        colorscale='RdBu',
        zmid=0,
        text=corr.values.round(2).tolist(),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Correlación")
    ))
    fig.update_layout(
        title='Matriz de Correlación - Materiales',
        xaxis={'side': 'bottom'},
        width=700,
        height=600
    )
    return _fig_to_obj(fig)


def _generar_correlacion_aditivos(df: pd.DataFrame, aditivos: list):
    """Genera matriz de correlación de aditivos."""
    aditivos = [c for c in aditivos if c in df.columns]
    if len(aditivos) < 2:
        return None
    
    corr = df[aditivos].corr(numeric_only=True)
    fig = go.Figure(data=go.Heatmap(
        z=corr.values.tolist(),
        x=corr.columns.tolist(),
        y=corr.columns.tolist(),
        colorscale='RdBu',
        zmid=0,
        text=corr.values.round(2).tolist(),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Correlación")
    ))
    fig.update_layout(
        title='Matriz de Correlación - Aditivos',
        xaxis={'side': 'bottom', 'tickangle': -45},
        width=800,
        height=700
    )
    return _fig_to_obj(fig)


def generar_graficas_json_desde_datos(df: pd.DataFrame) -> str:
    """Genera un JSON string con todas las gráficas apropiadas.
    
    Args:
        df: DataFrame con los datos filtrados
        
    Returns:
        str: JSON string con las gráficas
    """
    resultado = generar_graficas_desde_datos(df)
    return json.dumps(resultado, ensure_ascii=False, cls=PlotlyJSONEncoder)


if __name__ == "__main__":
    # Test con diferentes cantidades de datos
    print("Probando recomendaciones con diferentes tamaños de datos:\n")
    
    for n in [0, 1, 5, 10, 30, 50, 100]:
        rec = recomendar_graficas(n)
        print(f"Con {n} registros:")
        print(f"  Recomendadas: {len(rec['graficas_recomendadas'])} gráficas")
        print(f"  Advertencias: {rec['advertencias']}")
        print()
