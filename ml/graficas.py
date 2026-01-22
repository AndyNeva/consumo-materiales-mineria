"""
Funciones para generar gráficas finales usando Plotly en Python.
Cada función recibe datos (DataFrame o listas) y devuelve el JSON de la figura Plotly.
Incluye función para elegir una gráfica dinámica por nombre.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.utils import PlotlyJSONEncoder
import json




MATERIALES_COLS = ['arena_kg', 'grava_kg', 'cemento_kg', 'agua_kg']
ADITIVOS_COLS = [
    "aditivo_rheo_sika115", "aditivo_basf_sika200", "aditivo_delvo",
    "aditivo_glenium_7950", "aditivo_glenium_7970","aditivo_fibras"
]

def _fig_to_obj(fig):
    """
    Convierte figura Plotly a objeto JSON asegurando que los valores numéricos
    se mantengan como números, no como strings, y que las fechas se preserven.
    """
    plotly_json = fig.to_plotly_json()
    
    # Asegurar que los datos numéricos en traces se mantengan como números
    if 'data' in plotly_json:
        for trace in plotly_json['data']:
            # Solo procesar y si es necesario convertir números
            if 'y' in trace and trace['y'] is not None:
                processed_y = []
                for y in trace['y']:
                    # Si es un número, convertir a float
                    if isinstance(y, (int, float, np.number)):
                        processed_y.append(float(y))
                    # Si es string numérico, convertir a float
                    elif isinstance(y, str) and y.replace('.','',1).replace('-','',1).replace('e','',1).replace('E','',1).isdigit():
                        processed_y.append(float(y))
                    # Para otros tipos, mantener como está
                    else:
                        processed_y.append(y)
                trace['y'] = processed_y
            
            # Para x, mantener como está (puede ser fechas, categorías, etc)
            # Solo asegurar que sea una lista
            if 'x' in trace and trace['x'] is not None:
                if not isinstance(trace['x'], list):
                    trace['x'] = list(trace['x'])
    
    return json.loads(json.dumps(plotly_json, cls=PlotlyJSONEncoder))

def _plotly_template_dark():
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": "rgba(255,255,255,.92)"},
        "xaxis": {"gridcolor": "rgba(255,255,255,.08)", "zerolinecolor": "rgba(255,255,255,.10)"},
        "yaxis": {"gridcolor": "rgba(255,255,255,.08)", "zerolinecolor": "rgba(255,255,255,.10)"},
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
    }

def grafica_bar_volumen_por_dia(df):
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["fecha_dia"] = df["fecha"].dt.date
    g = df.dropna(subset=["fecha_dia"]).groupby("fecha_dia", as_index=False)["volumen_m3"].sum()
    g = g.sort_values("fecha_dia", ascending=True)
    
    # Asegurar que volumen_m3 sea numérico
    g["volumen_m3"] = pd.to_numeric(g["volumen_m3"], errors='coerce')
    
    # Convertir fecha_dia a datetime y luego a string ISO
    g["fecha_datetime"] = pd.to_datetime(g["fecha_dia"])
    # Convertir a strings ISO que Plotly interpreta como fechas
    fechas_str = g["fecha_datetime"].dt.strftime('%Y-%m-%d').tolist()
    
    # Usar go.Bar con fechas como strings ISO
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=fechas_str,
        y=g["volumen_m3"].tolist(),
        marker=dict(
            color='rgba(79,140,255,.75)',
            line=dict(color='rgba(79,140,255,1)', width=2)  # Borde visible
        ),
        name='Volumen'
    ))
    
    layout = _plotly_template_dark()
    layout.update({
        'title': "Volumen por día (m³)",
        'xaxis': {
            'title': 'Fecha',
            'type': 'date',  # Plotly interpretará los strings como fechas
            'gridcolor': 'rgba(255,255,255,.08)',
            'zerolinecolor': 'rgba(255,255,255,.10)'
        },
        'yaxis': {
            'title': 'Volumen (m³)',
            'gridcolor': 'rgba(255,255,255,.08)',
            'zerolinecolor': 'rgba(255,255,255,.10)'
        }
    })
    fig.update_layout(**layout)
    return _fig_to_obj(fig)



def grafica_bar_volumen_por_diseno(df):
    g = df.groupby("diseno")["volumen_m3"].sum().reset_index()
    g = g.sort_values("volumen_m3", ascending=False)
    
    # Asegurar que volumen_m3 sea numérico
    g["volumen_m3"] = pd.to_numeric(g["volumen_m3"], errors='coerce')
    
    # Usar go.Bar para mejor control
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=g["diseno"].tolist(),
        y=g["volumen_m3"].tolist(),
        marker=dict(
            color='rgba(79,140,255,.75)',
            line=dict(color='rgba(79,140,255,1)', width=2)  # Borde visible
        ),
        name='Volumen'
    ))
    
    fig.update_layout(
        title="Volumen por diseño (m³)",
        xaxis_title="Diseño",
        yaxis_title="Volumen (m³)",
        **_plotly_template_dark()
    )
    return _fig_to_obj(fig)


def grafica_boxplot_volumen(df):
    # Asegurar que volumen_m3 sea numérico
    df_clean = df.copy()
    df_clean["volumen_m3"] = pd.to_numeric(df_clean["volumen_m3"], errors='coerce')
    df_clean = df_clean.dropna(subset=["volumen_m3"])
    
    fig = go.Figure()
    fig.add_trace(go.Box(
        y=df_clean["volumen_m3"].tolist(),
        name='Volumen',
        marker=dict(
            color='rgba(79,140,255,.75)',
            line=dict(width=2)
        ),
        line=dict(width=2, color='rgba(79,140,255,1)')
    ))
    
    fig.update_layout(
        title="Distribución volumen (boxplot)",
        yaxis_title="Volumen (m³)",
        **_plotly_template_dark()
    )
    return _fig_to_obj(fig)

def grafica_hist_volumen(df):
    # Asegurar que volumen_m3 sea numérico
    df_clean = df.copy()
    df_clean["volumen_m3"] = pd.to_numeric(df_clean["volumen_m3"], errors='coerce')
    df_clean = df_clean.dropna(subset=["volumen_m3"])
    
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df_clean["volumen_m3"].tolist(),
        nbinsx=10,
        marker=dict(
            color='rgba(79,140,255,.75)',
            line=dict(color='rgba(79,140,255,1)', width=2)  # Borde visible
        ),
        name='Volumen'
    ))
    
    fig.update_layout(
        title="Histograma volumen",
        xaxis_title="Volumen (m³)",
        yaxis_title="Frecuencia",
        **_plotly_template_dark()
    )
    return _fig_to_obj(fig)

def grafica_corr(df):
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_cols) < 2:
        return None
    corr = df[numeric_cols].corr()
    fig = go.Figure(data=go.Heatmap(
        z=corr.values.tolist(),
        x=corr.columns.tolist(),
        y=corr.columns.tolist(),
        colorscale="Viridis"
    ))
    fig.update_layout(title="Matriz correlación", **_plotly_template_dark())
    return _fig_to_obj(fig)

def grafica_frecuencia_diseno(df):
    freqs = df["diseno"].value_counts().reset_index()
    freqs.columns = ["diseno", "frecuencia"]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=freqs["diseno"].tolist(),
        y=freqs["frecuencia"].tolist(),
        marker=dict(
            color='rgba(79,140,255,.75)',
            line=dict(color='rgba(79,140,255,1)', width=2)  # Borde visible
        ),
        name='Frecuencia'
    ))
    
    fig.update_layout(
        title="Frecuencia de diseños de mezcla",
        xaxis_title="Diseño",
        yaxis_title="Frecuencia",
        **_plotly_template_dark()
    )
    return _fig_to_obj(fig)

def grafica_boxplot_materiales(df):
    columnas_presentes = [c for c in MATERIALES_COLS if c in df.columns]
    if not columnas_presentes:
        return None
    
    # Colores distintos para cada material
    colores = [
        'rgba(251,146,60,0.7)',   # Naranja - Arena
        'rgba(100,116,139,0.7)',  # Gris - Grava
        'rgba(79,140,255,0.7)',   # Azul - Cemento
        'rgba(34,197,94,0.7)'     # Verde - Agua
    ]
    
    fig = go.Figure()
    for i, col in enumerate(columnas_presentes):
        valores = pd.to_numeric(df[col], errors='coerce').dropna().tolist()
        color = colores[i % len(colores)]
        
        fig.add_trace(go.Box(
            y=valores,
            name=col.replace('_kg', '').replace('_', ' ').title(),
            marker=dict(
                color=color,
                line=dict(width=2)
            ),
            line=dict(width=2)
        ))
    
    fig.update_layout(
        title="Boxplot de materiales",
        yaxis_title="Cantidad (kg)",
        xaxis_title="Material",
        **_plotly_template_dark()
    )
    return _fig_to_obj(fig)

def grafica_boxplot_aditivos(df):
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if not presentes:
        return None
    
    # Colores distintos para cada aditivo
    colores = [
        'rgba(79,140,255,0.7)',   # Azul
        'rgba(255,107,107,0.7)',  # Rojo
        'rgba(34,197,94,0.7)',    # Verde
        'rgba(168,85,247,0.7)',   # Morado
        'rgba(251,146,60,0.7)',   # Naranja
        'rgba(236,72,153,0.7)'    # Rosa
    ]
    
    fig = go.Figure()
    for i, col in enumerate(presentes):
        valores = pd.to_numeric(df[col], errors='coerce').dropna().tolist()
        if len(valores) > 0:
            color = colores[i % len(colores)]
            
            fig.add_trace(go.Box(
                y=valores,
                name=col.replace('aditivo_', '').replace('_', ' ').title(),
                marker=dict(
                    color=color,
                    line=dict(width=2)
                ),
                line=dict(width=2)
            ))
    
    fig.update_layout(
        title="Boxplot de aditivos",
        yaxis_title="Cantidad (kg o litros)",
        xaxis_title="Aditivo",
        xaxis_tickangle=-45,
        **_plotly_template_dark()
    )
    return _fig_to_obj(fig)

def grafica_hist_aditivos(df):
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if not presentes:
        return None
    
    # Colores distintos para cada aditivo
    colores = [
        'rgba(79,140,255,0.7)',   # Azul
        'rgba(255,107,107,0.7)',  # Rojo
        'rgba(34,197,94,0.7)',    # Verde
        'rgba(168,85,247,0.7)',   # Morado
        'rgba(251,146,60,0.7)',   # Naranja
        'rgba(236,72,153,0.7)'    # Rosa
    ]
    
    fig = go.Figure()
    for i, c in enumerate(presentes):
        serie = pd.to_numeric(df[c], errors='coerce').dropna().tolist()
        if len(serie) > 0:
            color = colores[i % len(colores)]
            # Obtener el color RGB para el borde (más oscuro)
            border_color = color.replace('0.7)', '1)')
            
            fig.add_trace(go.Histogram(
                x=serie,
                name=c.replace('aditivo_', '').replace('_', ' ').title(),
                opacity=0.7,
                nbinsx=30,
                marker=dict(
                    color=color,
                    line=dict(color=border_color, width=1.5)  # Borde
                )
            ))
    fig.update_layout(
        barmode='overlay',
        title="Histograma de aditivos",
        xaxis_title="Cantidad (kg o litros)",
        yaxis_title="Frecuencia",
        height=500,
        width=1000,
        showlegend=True,
        **_plotly_template_dark()
    )
    return _fig_to_obj(fig)

def grafica_corr_materiales(df):
    presentes = [c for c in MATERIALES_COLS if c in df.columns]
    if len(presentes) < 2:
        return None
    
    # Asegurar que todas las columnas sean numéricas
    df_numeric = df[presentes].apply(pd.to_numeric, errors='coerce')
    corr = df_numeric.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr.values.tolist(),
        x=corr.columns.tolist(),
        y=corr.columns.tolist(),
        colorscale='RdBu',
        zmid=0,
        text=corr.values.round(2).tolist(),
        texttemplate='%{text}',
        textfont={"size": 14},
        colorbar=dict(title="Correlación")
    ))
    layout = _plotly_template_dark().copy()
    layout.update({
        'title': 'Matriz de correlación - Materiales',
        'xaxis': {'side': 'bottom'},
        'width': 900,
        'height': 750
    })
    fig.update_layout(**layout)
    return _fig_to_obj(fig)

def grafica_corr_aditivos(df):
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if len(presentes) < 2:
        return None
    
    # Asegurar que todas las columnas sean numéricas
    df_numeric = df[presentes].apply(pd.to_numeric, errors='coerce')
    corr = df_numeric.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr.values.tolist(),
        x=corr.columns.tolist(),
        y=corr.columns.tolist(),
        colorscale='RdBu',
        zmid=0,
        text=corr.values.round(2).tolist(),
        texttemplate='%{text}',
        textfont={"size": 14},
        colorbar=dict(title="Correlación")
    ))
    layout = _plotly_template_dark().copy()
    layout.update({
        'title': 'Matriz de correlación - Aditivos',
        'xaxis': {'side': 'bottom', 'tickangle': -45},
        'width': 1000,
        'height': 850
    })
    fig.update_layout(**layout)
    return _fig_to_obj(fig)

def graficas_dinamicas(df):
    """
    Devuelve una LISTA ORDENADA con las gráficas recomendadas según el número de registros y columnas del DataFrame.
    Orden: volúmenes → histogramas → frecuencia → boxplots → heatmaps (al final).
    Cada elemento es un dict con 'nombre' y 'figura'.
    """
    graficas_lista = []
    n = int(df.shape[0]) if df is not None else 0
    
    # 1. Volúmenes (siempre mostrar primero)
    graficas_lista.append({"nombre": "volumen_por_dia", "figura": grafica_bar_volumen_por_dia(df)})
    graficas_lista.append({"nombre": "volumen_por_diseno", "figura": grafica_bar_volumen_por_diseno(df)})
    
    # 2. Histogramas (mostrar temprano para ver distribuciones)
    if n >= 30:
        graficas_lista.append({"nombre": "hist_volumen", "figura": grafica_hist_volumen(df)})
        graficas_lista.append({"nombre": "hist_aditivos", "figura": grafica_hist_aditivos(df)})
    
    # 3. Frecuencia de diseños si existe columna
    if ("diseno" in df.columns and n >= 5):
        graficas_lista.append({"nombre": "frecuencia_diseno", "figura": grafica_frecuencia_diseno(df)})
    
    # 4. Boxplots
    graficas_lista.append({"nombre": "boxplot_materiales", "figura": grafica_boxplot_materiales(df)})
    if n >= 10:
        graficas_lista.append({"nombre": "boxplot_aditivos", "figura": grafica_boxplot_aditivos(df)})
    
    # 5. Heatmaps al final (requieren más espacio)
    if n >= 50:
        graficas_lista.append({"nombre": "corr_materiales", "figura": grafica_corr_materiales(df)})
        graficas_lista.append({"nombre": "corr_aditivos", "figura": grafica_corr_aditivos(df)})

    return graficas_lista