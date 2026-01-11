import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import Tk, Toplevel, Text, Scrollbar, Button, filedialog, messagebox

ROOT = Tk()
ROOT.withdraw()  # Oculta la ventana principal de Tk

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

def limpiar_dataframe(df):
    """Convierte a numéricas las columnas relevantes y elimina filas completamente vacías.
    No falla si faltan columnas: solo convierte las que existan.
    """
    columnas_a_convertir = [c for c in MATERIALES_COLS + ADITIVOS_COLS if c in df.columns]
    if columnas_a_convertir:
        df[columnas_a_convertir] = df[columnas_a_convertir].apply(pd.to_numeric, errors='coerce')
    # Eliminar filas sin información en columnas clave
    if columnas_a_convertir:
        df = df.dropna(how='all', subset=columnas_a_convertir)
    return df

df = limpiar_dataframe(df)


def guardar_figura(fig, default_name):
    """Abre un diálogo para exportar la figura a imagen."""
    ruta = filedialog.asksaveasfilename(
        parent=ROOT,
        defaultextension=".png",
        filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("Todos", "*.*")],
        initialfile=default_name,
        title="Guardar gráfico",
    )

    if ruta:
        fig.savefig(ruta, dpi=300, bbox_inches='tight')
        messagebox.showinfo("Exportar", f"Gráfico exportado en {ruta}")


def mostrar_figura_en_ventana(fig, titulo, default_name="grafico.png"):
    """Muestra una figura de Matplotlib en una ventana con opción de exportar."""
    ventana = Toplevel(ROOT)
    ventana.title(titulo)

    canvas = FigureCanvasTkAgg(fig, master=ventana)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    Button(
        ventana,
        text="Exportar gráfico",
        command=lambda: guardar_figura(fig, default_name),
    ).pack(side='bottom', pady=8)

def mostrar_resultados_en_ventana(titulo, contenido):
    """Muestra resultados en una ventana de texto."""
    ventana = Toplevel(ROOT)
    ventana.title(titulo)

    text_area = Text(ventana, wrap='word', height=20, width=100)
    scroll = Scrollbar(ventana, command=text_area.yview)
    text_area.configure(yscrollcommand=scroll.set)
    text_area.insert('1.0', contenido)
    text_area.pack(side='left', fill='both', expand=True)
    scroll.pack(side='right', fill='y')

def generar_resumen_numerico(df):
    """Genera y muestra un resumen numérico de materiales y aditivos."""
    columnas_materiales = ['Arena (kg)', 'Grava (kg)', 'Cemento (kg)', 'Agua (kg)']
    columnas_todas = [c for c in columnas_materiales + ADITIVOS_COLS if c in df.columns]
    if not columnas_todas:
        messagebox.showwarning("Resumen", "No hay columnas de materiales/aditivos presentes para resumir.")
        return
    resumen = df[columnas_todas].describe()
    mostrar_resultados_en_ventana("Resumen Numérico (Materiales y Aditivos)", resumen.to_string())

def graficar_boxplot_materiales(df):
    """Genera un boxplot de los materiales usados para el concreto."""
    columnas_presentes = [c for c in ['Arena (kg)', 'Grava (kg)', 'Cemento (kg)', 'Agua (kg)'] if c in df.columns]
    if not columnas_presentes:
        messagebox.showwarning("Boxplot materiales", "No hay columnas de materiales presentes para graficar.")
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    df[columnas_presentes].boxplot(ax=ax)
    ax.set_title('Boxplot de los materiales usados para el concreto')
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    mostrar_figura_en_ventana(fig, "Boxplot de materiales", default_name="boxplot_materiales.png")
    plt.close(fig)

def graficar_frecuencia_disenos(df):
    """Genera un gráfico de barras con la frecuencia de diseños de mezcla."""
    try:
        mix_counts = df['Diseño de la Mezcla'].value_counts()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(mix_counts.index, mix_counts.values)
        ax.set_title('Frecuencia de Diseños de Mezcla')
        ax.set_xlabel('Diseño')
        ax.set_ylabel('Frecuencia')
        plt.setp(ax.get_xticklabels(), rotation=90, ha='center')
        mostrar_figura_en_ventana(fig, "Frecuencia de diseños", default_name="frecuencia_disenos.png")
        plt.close(fig)
    except KeyError as e:
        print(f"Error: {e}. Verifique que la columna 'Diseño de la Mezcla' exista en el DataFrame.")

def graficar_matriz_correlacion(df):
    """Genera un mapa de calor con la matriz de correlación."""
    heatmap_cols = ['Arena (kg)', 'Grava (kg)', 'Cemento (kg)', 'Agua (kg)', 'Volumen (m3)']
    presentes = [c for c in heatmap_cols if c in df.columns]
    if len(presentes) < 2:
        messagebox.showwarning("Correlación", "Se requieren al menos 2 columnas para correlacionar.")
        return
    heatmap_data = df[presentes]
    corr = heatmap_data.corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f', ax=ax)
    ax.set_title('Mapa de Calor de Correlaciones entre Materiales y Volumen')
    mostrar_figura_en_ventana(fig, "Matriz de correlación", default_name="matriz_correlacion.png")
    plt.close(fig)


def estadisticos_aditivos(df):
    """Muestra tabla descriptiva de aditivos."""
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if not presentes:
        messagebox.showwarning("Aditivos", "No hay columnas de aditivos presentes para resumir.")
        return
    desc = df[presentes].describe()
    mostrar_resultados_en_ventana(
        "Estadísticos de aditivos",
        desc.to_string()
    )


def graficar_aditivos_boxplot(df):
    """Boxplot de aditivos."""
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if not presentes:
        messagebox.showwarning("Boxplot aditivos", "No hay columnas de aditivos presentes para graficar.")
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    df[presentes].boxplot(ax=ax)
    ax.set_title('Boxplot de aditivos')
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    mostrar_figura_en_ventana(fig, "Boxplot de aditivos", default_name="boxplot_aditivos.png")
    plt.close(fig)


def graficar_aditivos_histograma(df):
    """Histograma de aditivos."""
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        columnas_presentes = [c for c in ADITIVOS_COLS if c in df.columns]
        if not columnas_presentes:
            raise KeyError("No hay columnas de aditivos presentes en el DataFrame.")
        datasets = [df[c].dropna().values for c in columnas_presentes]
        ax.hist(datasets, bins=20, label=columnas_presentes, alpha=0.6)
        ax.set_title('Histograma de aditivos')
        ax.set_xlabel('Cantidad')
        ax.set_ylabel('Frecuencia')
        ax.legend()
        mostrar_figura_en_ventana(fig, "Histograma de aditivos", default_name="histograma_aditivos.png")
        plt.close(fig)
    except KeyError as e:
        print(f"Error: {e}. Verifique que las columnas de aditivos existan en el DataFrame.")


def graficar_aditivos_heatmap(df):
    """Mapa de calor de correlación de aditivos."""
    presentes = [c for c in ADITIVOS_COLS if c in df.columns]
    if len(presentes) < 2:
        messagebox.showwarning("Correlación aditivos", "Se requieren al menos 2 columnas de aditivos para correlacionar.")
        return
    corr = df[presentes].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f', ax=ax)
    ax.set_title('Mapa de calor de correlación de aditivos')
    mostrar_figura_en_ventana(fig, "Correlación de aditivos", default_name="correlacion_aditivos.png")
    plt.close(fig)


def lanzar_menu():
    """Muestra una ventana con botones para ejecutar cada análisis."""
    ROOT.deiconify()
    ROOT.title("Panel de análisis de materiales")

    Button(ROOT, text="Resumen numérico", width=30, command=lambda: generar_resumen_numerico(df)).pack(pady=5)
    Button(ROOT, text="Boxplot de materiales", width=30, command=lambda: graficar_boxplot_materiales(df)).pack(pady=5)
    Button(ROOT, text="Frecuencia de diseños", width=30, command=lambda: graficar_frecuencia_disenos(df)).pack(pady=5)
    Button(ROOT, text="Matriz de correlación de materiales", width=30, command=lambda: graficar_matriz_correlacion(df)).pack(pady=5)
    Button(ROOT, text="Boxplot de aditivos", width=30, command=lambda: graficar_aditivos_boxplot(df)).pack(pady=5)
    Button(ROOT, text="Histograma de aditivos", width=30, command=lambda: graficar_aditivos_histograma(df)).pack(pady=5)
    Button(ROOT, text="Heatmap de aditivos", width=30, command=lambda: graficar_aditivos_heatmap(df)).pack(pady=5)
    Button(ROOT, text="Salir", width=30, command=ROOT.destroy).pack(pady=10)

    ROOT.mainloop()


if __name__ == "__main__":
    lanzar_menu()
