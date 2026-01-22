"""
Generador de gráficos Plotly con layout oscuro para consumo de materiales.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from ml.estadisticas_dinamicas import _plotly_template_dark

# Ejemplo: Boxplot de volumen

def plot_boxplot_volumen(df: pd.DataFrame, col_vol: str = "volumen_m3"):
    if col_vol not in df.columns:
        raise ValueError(f"Columna '{col_vol}' no encontrada en el DataFrame.")
    fig = px.box(df, y=col_vol, title="Distribución de Volumen (Boxplot)")
    fig.update_layout(**_plotly_template_dark())
    return fig

# Ejemplo: Histograma de volumen

def plot_hist_volumen(df: pd.DataFrame, col_vol: str = "volumen_m3"):
    if col_vol not in df.columns:
        raise ValueError(f"Columna '{col_vol}' no encontrada en el DataFrame.")
    fig = px.histogram(df, x=col_vol, nbins=10, title="Histograma de Volumen")
    fig.update_layout(**_plotly_template_dark())
    return fig

# Ejemplo: Frecuencia de diseños

def plot_frecuencia_diseno(df: pd.DataFrame, col_diseno: str = "diseno_mezcla"):
    if col_diseno not in df.columns:
        raise ValueError(f"Columna '{col_diseno}' no encontrada en el DataFrame.")
    freqs = df[col_diseno].value_counts().reset_index()
    freqs.columns = ["Diseño", "Frecuencia"]
    fig = px.bar(freqs, x="Diseño", y="Frecuencia", title="Frecuencia de Diseños de Mezcla")
    fig.update_layout(**_plotly_template_dark())
    return fig

# Ejemplo: Matriz de correlación

def plot_matriz_correlacion(df: pd.DataFrame, cols: list):
    df_corr = df[cols].corr(numeric_only=True)
    fig = go.Figure(data=go.Heatmap(
        z=df_corr.values,
        x=df_corr.columns,
        y=df_corr.columns,
        colorscale='RdBu',
        zmid=0,
        text=df_corr.values.round(2),
        texttemplate='%{text}',
        colorbar=dict(title="Correlación")
    ))
    fig.update_layout(title="Matriz de Correlación", **_plotly_template_dark())
    return fig

# Puedes agregar más funciones según los tipos de gráficos que necesites.
