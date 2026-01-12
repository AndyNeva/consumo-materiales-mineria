from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder

# Cargar el archivo CSV desde el mismo directorio del script
BASE_DIR = Path(__file__).resolve().parent
DATOS = BASE_DIR / "Datos_Stat_Model.csv"

if not DATOS.exists():
    raise FileNotFoundError(f"No se encontro el archivo de datos esperado en {DATOS}")

df = pd.read_csv(DATOS)

# Conversión robusta de columnas numéricas
MATERIALES_COLS = ['Arena (kg)', 'Grava (kg)', 'Cemento (kg)', 'Agua (kg)']

# Definir aditivos antes de usarlos en limpieza
ADITIVOS_COLS = [
    'RHEO 1000 (kg)',
    'BASF 719 (kg)',
    'Delvo (litros)',
    'MasterGlenium 7950',
    'MasterGlenium 7970',
    'Sika PP 48 (kg)-BARCHIP',
]


def limpiar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte a numéricas las columnas relevantes y elimina filas completamente vacías.
    No falla si faltan columnas: solo convierte las que existan.
    """
    columnas_a_convertir = [c for c in MATERIALES_COLS + ADITIVOS_COLS if c in df.columns]
    if columnas_a_convertir:
        df[columnas_a_convertir] = df[columnas_a_convertir].apply(pd.to_numeric, errors='coerce')
        df = df.dropna(how='all', subset=columnas_a_convertir)
    return df


df = limpiar_dataframe(df)


def _output_dir() -> Path:
    """Directorio de salida para el JSON unificado (ml/graficas)."""
    out = BASE_DIR / "graficas"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _fig_to_obj(fig) -> dict:
    """Convierte figura Plotly a objeto dict (data+layout)."""
    return fig.to_plotly_json()


def _save_single_json(data: dict, filename: str) -> Path:
    import json
    path = _output_dir() / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, cls=PlotlyJSONEncoder), encoding="utf-8")
    return path


def generar_resumen_numerico(df: pd.DataFrame) -> dict | None:
    """Genera resumen numérico (describe) y lo retorna como dict.
    Retorna None si no hay columnas aplicables.
    """
    columnas_todas = [c for c in MATERIALES_COLS + ADITIVOS_COLS if c in df.columns]
    if not columnas_todas:
        return None
    resumen = df[columnas_todas].describe().to_dict()
    return resumen


def graficar_boxplot_materiales(df: pd.DataFrame):
    """Crea boxplot de materiales con Plotly y retorna el objeto figura (dict)."""
    columnas_presentes = [c for c in MATERIALES_COLS if c in df.columns]
    if not columnas_presentes:
        return None
    df_long = df[columnas_presentes].melt(var_name="Material", value_name="Cantidad")
    fig = px.box(df_long, x="Material", y="Cantidad", title="Boxplot de materiales (Plotly)")
    fig.update_layout(xaxis_tickangle=-45)
    return _fig_to_obj(fig)


def graficar_frecuencia_disenos(df: pd.DataFrame):
    """Crea gráfico de barras de frecuencia de diseños de mezcla y retorna dict."""
    if 'Diseño de la Mezcla' not in df.columns:
        return None
    mix_counts = df['Diseño de la Mezcla'].value_counts().reset_index()
    mix_counts.columns = ['Diseño', 'Frecuencia']
    fig = px.bar(mix_counts, x='Diseño', y='Frecuencia', title='Frecuencia de Diseños de Mezcla (Plotly)')
    fig.update_layout(xaxis_tickangle=-90)
    return _fig_to_obj(fig)


def graficar_matriz_correlacion(df: pd.DataFrame):
    """Crea heatmap de correlaciones entre materiales/volumen y retorna dict."""
    heatmap_cols = MATERIALES_COLS + ['Volumen (m3)']
    presentes = [c for c in heatmap_cols if c in df.columns]
    if len(presentes) < 2:
        return None
    corr = df[presentes].corr(numeric_only=True)
    fig = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu', origin='lower',
                    title='Matriz de correlación (Plotly)')
    return _fig_to_obj(fig)


def estadisticos_aditivos(df: pd.DataFrame) -> dict | None:
    """Genera describe() de aditivos y retorna dict."""
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if not presentes:
        return None
    desc = df[presentes].describe().to_dict()
    return desc


def graficar_aditivos_boxplot(df: pd.DataFrame):
    """Crea boxplot de aditivos con Plotly y retorna dict."""
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if not presentes:
        return None
    df_long = df[presentes].melt(var_name="Aditivo", value_name="Cantidad")
    fig = px.box(df_long, x="Aditivo", y="Cantidad", title="Boxplot de aditivos (Plotly)")
    fig.update_layout(xaxis_tickangle=-45)
    return _fig_to_obj(fig)


def graficar_aditivos_histograma(df: pd.DataFrame):
    """Crea histograma superpuesto de aditivos con Plotly y retorna dict."""
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if not presentes:
        return None
    fig = go.Figure()
    for c in presentes:
        serie = df[c].dropna()
        fig.add_trace(go.Histogram(x=serie, name=c, opacity=0.6))
    fig.update_layout(barmode='overlay', title="Histograma de aditivos (Plotly)")
    fig.update_traces(nbinsx=20)
    fig.update_xaxes(title_text="Cantidad")
    fig.update_yaxes(title_text="Frecuencia")
    return _fig_to_obj(fig)


def graficar_aditivos_heatmap(df: pd.DataFrame):
    """Crea heatmap de correlación de aditivos con Plotly y retorna dict."""
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if len(presentes) < 2:
        return None
    corr = df[presentes].corr(numeric_only=True)
    fig = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu', origin='lower',
                    title='Correlación de aditivos (Plotly)')
    return _fig_to_obj(fig)


def exportar_todo_a_json(filename: str = "graficas.json") -> Path:
    """Genera todas las salidas (figuras y resúmenes) y guarda TODO en un solo
    archivo JSON dentro de ml/graficas. Retorna la ruta del archivo.
    Estructura del JSON:
    {
      "boxplot_materiales": {"data": [...], "layout": {...}},
      "frecuencia_disenos": {"data": [...], "layout": {...}},
      "matriz_correlacion_materiales": {"data": [...], "layout": {...}},
      "boxplot_aditivos": {"data": [...], "layout": {...}},
      "histograma_aditivos": {"data": [...], "layout": {...}},
      "correlacion_aditivos": {"data": [...], "layout": {...}},
      "resumen_numerico": {...},
      "estadisticos_aditivos": {...}
    }
    """
    bundle: dict = {}

    # Figuras Plotly
    fig_box_mat = graficar_boxplot_materiales(df)
    if fig_box_mat is not None:
        bundle['boxplot_materiales'] = fig_box_mat

    fig_freq = graficar_frecuencia_disenos(df)
    if fig_freq is not None:
        bundle['frecuencia_disenos'] = fig_freq

    fig_corr_mat = graficar_matriz_correlacion(df)
    if fig_corr_mat is not None:
        bundle['matriz_correlacion_materiales'] = fig_corr_mat

    fig_box_adit = graficar_aditivos_boxplot(df)
    if fig_box_adit is not None:
        bundle['boxplot_aditivos'] = fig_box_adit

    fig_hist_adit = graficar_aditivos_histograma(df)
    if fig_hist_adit is not None:
        bundle['histograma_aditivos'] = fig_hist_adit

    fig_corr_adit = graficar_aditivos_heatmap(df)
    if fig_corr_adit is not None:
        bundle['correlacion_aditivos'] = fig_corr_adit

    # Resúmenes numéricos
    resumen_num = generar_resumen_numerico(df)
    if resumen_num is not None:
        bundle['resumen_numerico'] = resumen_num

    desc_adit = estadisticos_aditivos(df)
    if desc_adit is not None:
        bundle['estadisticos_aditivos'] = desc_adit

    # Guardar un único archivo
    return _save_single_json(bundle, filename)


if __name__ == "__main__":
    # Si se llama directamente (poco común en esta app), exporta todo.
    exportar_todo_a_json()
