from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder

# Cargar el archivo CSV desde el mismo directorio del script
BASE_DIR = Path(__file__).resolve().parent
DATOS = BASE_DIR / "DatosLimpios.csv"

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


# ==========================================
# APARTADO: GENERACIÓN DE IMÁGENES PNG
# ==========================================

def _crear_figura_desde_dict(fig_dict):
    """Reconstruye una figura de Plotly desde un diccionario."""
    if fig_dict is None:
        return None
    return go.Figure(data=fig_dict.get('data', []), layout=fig_dict.get('layout', {}))


def generar_imagenes_png():
    """Genera todas las gráficas como imágenes PNG en la carpeta graficas.
    Retorna un diccionario con las rutas de los archivos generados.
    """
    output_dir = _output_dir()
    rutas_generadas = {}
    
    print("Generando imagenes PNG de las graficas...")
    print(f"Carpeta de destino: {output_dir}")
    print("-" * 60)
    
    # 1. Boxplot de materiales
    try:
        fig_dict = graficar_boxplot_materiales(df)
        if fig_dict:
            fig = _crear_figura_desde_dict(fig_dict)
            ruta = output_dir / "boxplot_materiales.png"
            fig.write_image(str(ruta), width=1200, height=600)
            rutas_generadas['boxplot_materiales'] = str(ruta)
            print("[OK] boxplot_materiales.png")
    except Exception as e:
        print(f"[ERROR] boxplot_materiales: {e}")
    
    # 2. Frecuencia de diseños
    try:
        fig_dict = graficar_frecuencia_disenos(df)
        if fig_dict:
            fig = _crear_figura_desde_dict(fig_dict)
            ruta = output_dir / "frecuencia_disenos.png"
            fig.write_image(str(ruta), width=1200, height=600)
            rutas_generadas['frecuencia_disenos'] = str(ruta)
            print("[OK] frecuencia_disenos.png")
    except Exception as e:
        print(f"[ERROR] frecuencia_disenos: {e}")
    
    # 3. Matriz de correlación de materiales
    try:
        fig_dict = graficar_matriz_correlacion(df)
        if fig_dict:
            fig = _crear_figura_desde_dict(fig_dict)
            ruta = output_dir / "matriz_correlacion_materiales.png"
            fig.write_image(str(ruta), width=1000, height=800)
            rutas_generadas['matriz_correlacion_materiales'] = str(ruta)
            print("[OK] matriz_correlacion_materiales.png")
    except Exception as e:
        print(f"[ERROR] matriz_correlacion: {e}")
    
    # 4. Boxplot de aditivos
    try:
        fig_dict = graficar_aditivos_boxplot(df)
        if fig_dict:
            fig = _crear_figura_desde_dict(fig_dict)
            ruta = output_dir / "boxplot_aditivos.png"
            fig.write_image(str(ruta), width=1200, height=600)
            rutas_generadas['boxplot_aditivos'] = str(ruta)
            print("[OK] boxplot_aditivos.png")
    except Exception as e:
        print(f"[ERROR] boxplot_aditivos: {e}")
    
    # 5. Histograma de aditivos
    try:
        fig_dict = graficar_aditivos_histograma(df)
        if fig_dict:
            fig = _crear_figura_desde_dict(fig_dict)
            ruta = output_dir / "histograma_aditivos.png"
            fig.write_image(str(ruta), width=1200, height=600)
            rutas_generadas['histograma_aditivos'] = str(ruta)
            print("[OK] histograma_aditivos.png")
    except Exception as e:
        print(f"[ERROR] histograma_aditivos: {e}")
    
    # 6. Heatmap de correlación de aditivos
    try:
        fig_dict = graficar_aditivos_heatmap(df)
        if fig_dict:
            fig = _crear_figura_desde_dict(fig_dict)
            ruta = output_dir / "correlacion_aditivos.png"
            fig.write_image(str(ruta), width=1000, height=800)
            rutas_generadas['correlacion_aditivos'] = str(ruta)
            print("[OK] correlacion_aditivos.png")
    except Exception as e:
        print(f"[ERROR] correlacion_aditivos: {e}")
    
    # 7. Tabla de resumen numérico
    try:
        columnas_todas = [c for c in MATERIALES_COLS + ADITIVOS_COLS if c in df.columns]
        if columnas_todas:
            resumen = df[columnas_todas].describe()
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=['Estadistico'] + list(resumen.columns),
                    fill_color='paleturquoise',
                    align='left',
                    font=dict(size=12, color='black')
                ),
                cells=dict(
                    values=[resumen.index] + [resumen[col].round(2) for col in resumen.columns],
                    fill_color='lavender',
                    align='left',
                    font=dict(size=11)
                )
            )])
            fig.update_layout(title="Resumen Numerico - Materiales y Aditivos", height=500)
            ruta = output_dir / "resumen_numerico.png"
            fig.write_image(str(ruta), width=1400, height=600)
            rutas_generadas['resumen_numerico'] = str(ruta)
            print("[OK] resumen_numerico.png")
    except Exception as e:
        print(f"[ERROR] resumen_numerico: {e}")
    
    # 8. Tabla de estadísticos de aditivos
    try:
        presentes = [c for c in ADITIVOS_COLS if c in df.columns]
        if presentes:
            desc = df[presentes].describe()
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=['Estadistico'] + list(desc.columns),
                    fill_color='lightcoral',
                    align='left',
                    font=dict(size=12, color='black')
                ),
                cells=dict(
                    values=[desc.index] + [desc[col].round(2) for col in desc.columns],
                    fill_color='mistyrose',
                    align='left',
                    font=dict(size=11)
                )
            )])
            fig.update_layout(title="Estadisticos Descriptivos - Aditivos", height=500)
            ruta = output_dir / "estadisticos_aditivos.png"
            fig.write_image(str(ruta), width=1400, height=600)
            rutas_generadas['estadisticos_aditivos'] = str(ruta)
            print("[OK] estadisticos_aditivos.png")
    except Exception as e:
        print(f"[ERROR] estadisticos_aditivos: {e}")
    
    print("-" * 60)
    print(f"Proceso completado. Total: {len(rutas_generadas)} imagenes generadas.")
    print(f"Ubicacion: {output_dir}")
    
    return rutas_generadas


if __name__ == "__main__":
    # Si se llama directamente (poco común en esta app), exporta todo.
    exportar_todo_a_json()
    
    # Generar imágenes PNG para verificación visual
    print("\n" + "=" * 60)
    generar_imagenes_png()
