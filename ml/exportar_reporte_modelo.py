"""
Script para generar un reporte PDF completo del modelo de predicción de materiales.
"""
import pickle
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.colors import HexColor

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / 'modelo_prediccion_materiales.pkl'
DOCS_DIR = BASE_DIR.parent / 'docs'
DOCS_DIR.mkdir(exist_ok=True)
PDF_PATH = DOCS_DIR / 'Reporte_Modelo_Prediccion_Materiales.pdf'

# Verificar que exista el modelo
if not MODEL_PATH.exists():
    raise FileNotFoundError(f"No se encontró el modelo en {MODEL_PATH}")

# Cargar el modelo y metadata
with open(MODEL_PATH, 'rb') as f:
    model_data = pickle.load(f)

# Crear el documento PDF
doc = SimpleDocTemplate(
    str(PDF_PATH),
    pagesize=letter,
    rightMargin=0.75*inch,
    leftMargin=0.75*inch,
    topMargin=0.75*inch,
    bottomMargin=0.75*inch
)

# Estilos
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name='CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=HexColor('#1f4788'),
    spaceAfter=30,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
))
styles.add(ParagraphStyle(
    name='CustomHeading2',
    parent=styles['Heading2'],
    fontSize=16,
    textColor=HexColor('#2e5fa3'),
    spaceAfter=12,
    spaceBefore=12,
    fontName='Helvetica-Bold'
))
styles.add(ParagraphStyle(
    name='CustomHeading3',
    parent=styles['Heading3'],
    fontSize=14,
    textColor=HexColor('#4a7bb7'),
    spaceAfter=10,
    spaceBefore=10,
    fontName='Helvetica-Bold'
))
styles.add(ParagraphStyle(
    name='CustomBody',
    parent=styles['BodyText'],
    fontSize=11,
    alignment=TA_JUSTIFY,
    spaceAfter=12
))
styles.add(ParagraphStyle(
    name='CustomBullet',
    parent=styles['BodyText'],
    fontSize=10,
    leftIndent=20,
    spaceAfter=6
))

# Contenido del PDF
story = []

# ========== PORTADA ==========
story.append(Spacer(1, 1.5*inch))
story.append(Paragraph(
    "REPORTE TÉCNICO",
    styles['CustomTitle']
))
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph(
    "Modelo de Predicción de Consumo de Materiales<br/>en Plantas de Producción de Concreto",
    styles['CustomTitle']
))
story.append(Spacer(1, 0.5*inch))

# Información general
info_portada = [
    ["Modelo:", model_data['model_name']],
    ["Fecha de Generación:", datetime.now().strftime("%d/%m/%Y %H:%M")],
    ["R² Score:", f"{model_data['metricas']['r2_global']:.4f}"],
    ["RMSE:", f"{model_data['metricas']['rmse_global']:.2f} kg"],
    ["MAE:", f"{model_data['metricas']['mae_global']:.2f} kg"],
]
tabla_portada = Table(info_portada, colWidths=[2*inch, 3*inch])
tabla_portada.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (0, -1), HexColor('#e8f0f7')),
    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 0), (-1, -1), 12),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ('TOPPADDING', (0, 0), (-1, -1), 12),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
]))
story.append(tabla_portada)
story.append(PageBreak())

# ========== RESUMEN EJECUTIVO ==========
story.append(Paragraph("1. RESUMEN EJECUTIVO", styles['CustomHeading2']))
story.append(Paragraph(
    "El presente documento detalla el desarrollo e implementación de un modelo predictivo de aprendizaje "
    "automático diseñado para estimar con alta precisión las cantidades necesarias de materiales (Arena, Grava "
    "y Cemento) en la producción de concreto. El modelo alcanza un coeficiente de determinación (R²) de 0.9987, "
    "explicando el 99.87% de la varianza en los datos de validación.",
    styles['CustomBody']
))
story.append(Paragraph(
    "<b>Objetivo Principal:</b> Predecir el consumo de materiales basándose en variables temporales, "
    "operativas y de diseño de mezcla, facilitando la planificación de inventarios y optimización de costos.",
    styles['CustomBody']
))
story.append(Spacer(1, 0.2*inch))

# ========== ARQUITECTURA DEL MODELO ==========
story.append(Paragraph("2. ARQUITECTURA DEL MODELO", styles['CustomHeading2']))

story.append(Paragraph("2.1 Variables de Entrada", styles['CustomHeading3']))
story.append(Paragraph(
    f"El modelo utiliza <b>{len(model_data['features'])} características</b> distribuidas en tres categorías:",
    styles['CustomBody']
))

# Tabla de categorías de features
categorias_features = [
    ["Categoría", "Cantidad", "Descripción"],
    ["Variables Temporales", "14", "Fecha numérica, términos polinómicos, codificación cíclica (sen/cos)"],
    ["Variables Operativas", "10", "Turno, volumen, humedad, agua, aditivos químicos"],
    ["Diseño de Mezcla", "10", "One-hot encoding de los 10 diseños más frecuentes + OTROS"],
]
tabla_cat = Table(categorias_features, colWidths=[1.8*inch, 1*inch, 3.5*inch])
tabla_cat.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2e5fa3')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 11),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#f5f5f5')]),
]))
story.append(tabla_cat)
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("2.2 Variables de Salida", styles['CustomHeading3']))
target_list = "<br/>".join([f"• {t}" for t in model_data['targets']])
story.append(Paragraph(target_list, styles['CustomBullet']))
story.append(Spacer(1, 0.15*inch))

# ========== DATOS DE ENTRENAMIENTO ==========
story.append(Paragraph("3. DATOS DE ENTRENAMIENTO", styles['CustomHeading2']))
story.append(Paragraph(
    f"<b>Rango Temporal:</b> {model_data['fecha_min'].strftime('%d/%m/%Y')} - "
    f"{model_data['fecha_max'].strftime('%d/%m/%Y')}",
    styles['CustomBody']
))
story.append(Paragraph(
    "<b>Partición de Datos:</b> 80% entrenamiento (5,147 registros), 20% validación (1,287 registros)",
    styles['CustomBody']
))
story.append(Paragraph(
    "<b>Preprocesamiento:</b>",
    styles['CustomBody']
))
prepro_bullets = [
    "Eliminación de valores faltantes",
    "Conversión de fechas a formato datetime",
    "Ingeniería de características: términos polinómicos, codificación cíclica",
    "Normalización con StandardScaler (fit solo en entrenamiento)",
    "One-hot encoding de variables categóricas"
]
for bullet in prepro_bullets:
    story.append(Paragraph(f"• {bullet}", styles['CustomBullet']))
story.append(Spacer(1, 0.15*inch))

# ========== METODOLOGÍA ==========
story.append(Paragraph("4. METODOLOGÍA", styles['CustomHeading2']))

story.append(Paragraph("4.1 Algoritmos Evaluados", styles['CustomHeading3']))
story.append(Paragraph(
    "Se entrenaron y compararon tres algoritmos de ensemble, todos envueltos en <b>MultiOutputRegressor</b> "
    "para predicción simultánea de los tres materiales:",
    styles['CustomBody']
))

# Tabla de modelos
modelos_comp = [
    ["Modelo", "R² Validación", "RMSE (kg)", "MAE (kg)"],
    ["Random Forest", "0.9982", "84.45", "10.89"],
    ["Gradient Boosting ✓", "0.9987", "71.55", "10.15"],
    ["XGBoost", "0.9986", "75.55", "7.29"],
]
tabla_modelos = Table(modelos_comp, colWidths=[2.3*inch, 1.5*inch, 1.5*inch, 1.5*inch])
tabla_modelos.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2e5fa3')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('BACKGROUND', (0, 2), (-1, 2), HexColor('#d4edda')),  # Mejor modelo
]))
story.append(tabla_modelos)
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("4.2 Hiperparámetros del Modelo Seleccionado", styles['CustomHeading3']))
hiperparam_bullets = [
    "<b>Algoritmo:</b> Gradient Boosting Regressor",
    "<b>Estimadores:</b> 400 árboles",
    "<b>Profundidad Máxima:</b> 4",
    "<b>Tasa de Aprendizaje:</b> 0.05",
    "<b>Random State:</b> 42 (reproducibilidad)"
]
for bullet in hiperparam_bullets:
    story.append(Paragraph(f"• {bullet}", styles['CustomBullet']))
story.append(Spacer(1, 0.15*inch))

# ========== RESULTADOS ==========
story.append(PageBreak())
story.append(Paragraph("5. RESULTADOS Y MÉTRICAS", styles['CustomHeading2']))

story.append(Paragraph("5.1 Métricas Globales", styles['CustomHeading3']))
metricas_globales = [
    ["Métrica", "Valor", "Interpretación"],
    ["R² Score", f"{model_data['metricas']['r2_global']:.4f}", "Varianza explicada"],
    ["RMSE", f"{model_data['metricas']['rmse_global']:.2f} kg", "Error promedio cuadrático"],
    ["MAE", f"{model_data['metricas']['mae_global']:.2f} kg", "Error absoluto medio"],
]
tabla_metricas = Table(metricas_globales, colWidths=[1.8*inch, 1.5*inch, 3*inch])
tabla_metricas.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2e5fa3')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (1, -1), 'LEFT'),
    ('ALIGN', (2, 0), (2, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#f5f5f5')]),
]))
story.append(tabla_metricas)
story.append(Spacer(1, 0.2*inch))

story.append(Paragraph("5.2 Ejemplos de Predicción", styles['CustomHeading3']))
story.append(Paragraph(
    "Predicciones generadas para fechas futuras con parámetros de entrada representativos:",
    styles['CustomBody']
))

ejemplos_pred = [
    ["Fecha", "Arena (kg)", "Grava (kg)", "Cemento (kg)"],
    ["15/01/2026", "9,527.63", "2.51", "3,097.25"],
    ["15/02/2026", "9,462.03", "3.27", "3,118.27"],
    ["15/06/2026", "8,115.81", "84.92", "2,556.23"],
]
tabla_ejemplos = Table(ejemplos_pred, colWidths=[1.5*inch, 1.8*inch, 1.8*inch, 1.8*inch])
tabla_ejemplos.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2e5fa3')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#f5f5f5')]),
]))
story.append(tabla_ejemplos)
story.append(Spacer(1, 0.2*inch))

# ========== GRÁFICOS ==========
story.append(PageBreak())
story.append(Paragraph("6. VISUALIZACIONES", styles['CustomHeading2']))

# Incluir gráficos si existen
grafico_detallado = BASE_DIR / 'prediccion_materiales_detallado.png'
grafico_comparacion = BASE_DIR / 'comparacion_modelos.png'
grafico_serie = BASE_DIR / 'serie_tiempo_materiales.png'

if grafico_comparacion.exists():
    story.append(Paragraph("6.1 Comparación de Modelos", styles['CustomHeading3']))
    img_comp = Image(str(grafico_comparacion), width=6.5*inch, height=2.2*inch)
    story.append(img_comp)
    story.append(Spacer(1, 0.15*inch))

if grafico_detallado.exists():
    story.append(PageBreak())
    story.append(Paragraph("6.2 Análisis Detallado por Material", styles['CustomHeading3']))
    story.append(Paragraph(
        "Scatter plots de valores reales vs predicciones, análisis de residuos y distribuciones para cada material:",
        styles['CustomBody']
    ))
    img_det = Image(str(grafico_detallado), width=6.5*inch, height=6.5*inch)
    story.append(img_det)

if grafico_serie.exists():
    story.append(PageBreak())
    story.append(Paragraph("6.3 Serie Temporal: Real vs Predicción", styles['CustomHeading3']))
    img_serie = Image(str(grafico_serie), width=6.5*inch, height=5*inch)
    story.append(img_serie)
    story.append(Spacer(1, 0.15*inch))

# ========== CARACTERÍSTICAS TÉCNICAS ==========
story.append(PageBreak())
story.append(Paragraph("7. CARACTERÍSTICAS TÉCNICAS", styles['CustomHeading2']))

story.append(Paragraph("7.1 Ingeniería de Características", styles['CustomHeading3']))
ing_features_bullets = [
    "<b>Términos Polinómicos:</b> Fecha lineal, cuadrática y cúbica para capturar tendencias no lineales",
    "<b>Codificación Cíclica:</b> Sen/Cos de mes, día del año y semana para patrones estacionales continuos",
    "<b>Variables de Calendario:</b> Mes, día del año, semana del año, año",
    "<b>One-Hot Encoding:</b> Top 10 diseños de mezcla + categoría 'OTROS'",
    "<b>Variables Numéricas:</b> Volumen, humedad, agua y 6 tipos de aditivos"
]
for bullet in ing_features_bullets:
    story.append(Paragraph(f"• {bullet}", styles['CustomBullet']))
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("7.2 Función de Predicción", styles['CustomHeading3']))
story.append(Paragraph(
    "El modelo incluye una función <b>predecir_materiales()</b> que acepta:",
    styles['CustomBody']
))
funcion_params = [
    "<b>fecha_str:</b> Fecha en formato 'YYYY-MM-DD'",
    "<b>turno:</b> 'DIA' o 'NOCHE'",
    "<b>diseno:</b> Código del diseño de mezcla",
    "<b>Variables numéricas:</b> volumen, humedad, agua, y 6 aditivos"
]
for param in funcion_params:
    story.append(Paragraph(f"• {param}", styles['CustomBullet']))
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph(
    "La función construye el vector completo de 34 características, aplica normalización y retorna "
    "las cantidades predichas en kg.",
    styles['CustomBody']
))
story.append(Spacer(1, 0.2*inch))

# ========== ARTEFACTOS GUARDADOS ==========
story.append(Paragraph("8. ARTEFACTOS GENERADOS", styles['CustomHeading2']))
artefactos_list = [
    "<b>modelo_prediccion_materiales.pkl:</b> Modelo entrenado + escaladores + metadata",
    "<b>prediccion_materiales_detallado.png:</b> Gráficos de scatter, residuos y distribuciones",
    "<b>serie_tiempo_materiales.png:</b> Comparación temporal real vs predicción",
    "<b>comparacion_modelos.png:</b> Métricas comparativas de los 3 algoritmos"
]
for artefacto in artefactos_list:
    story.append(Paragraph(f"• {artefacto}", styles['CustomBullet']))
story.append(Spacer(1, 0.2*inch))

# ========== LIMITACIONES ==========
story.append(Paragraph("9. LIMITACIONES Y CONSIDERACIONES", styles['CustomHeading2']))
limitaciones = [
    "<b>MAPE de Grava:</b> Métrica inflada debido a valores muy cercanos a cero en el denominador. "
    "Se recomienda usar MAE/RMSE para Grava.",
    "<b>Extrapolación Temporal:</b> El modelo está entrenado hasta diciembre de 2025. Predicciones "
    "muy alejadas de este rango pueden perder precisión.",
    "<b>Diseños No Vistos:</b> Diseños fuera del top-10 se mapean a 'OTROS', perdiendo especificidad.",
    "<b>Dependencia de Aditivos:</b> Requiere conocer las cantidades de aditivos a priori, lo que puede "
    "ser difícil en etapas tempranas de planificación."
]
for lim in limitaciones:
    story.append(Paragraph(f"• {lim}", styles['CustomBullet']))
story.append(Spacer(1, 0.2*inch))

# ========== CONCLUSIONES ==========
story.append(Paragraph("10. CONCLUSIONES", styles['CustomHeading2']))
story.append(Paragraph(
    "El modelo de Gradient Boosting desarrollado demuestra una capacidad excepcional para predecir el consumo "
    "de materiales en plantas de concreto, alcanzando un R² de 0.9987. La combinación de ingeniería de "
    "características sofisticada (términos polinómicos, codificación cíclica) con un algoritmo de ensemble "
    "robusto permite capturar tanto tendencias a largo plazo como patrones estacionales.",
    styles['CustomBody']
))
story.append(Paragraph(
    "El modelo está listo para producción, con funciones de inferencia empaquetadas y artefactos completos "
    "para despliegue. Se recomienda reentrenamiento periódico con datos actualizados para mantener la precisión.",
    styles['CustomBody']
))
story.append(Spacer(1, 0.3*inch))

# Pie de página con información adicional
story.append(Paragraph("_" * 80, styles['CustomBody']))
story.append(Paragraph(
    f"<b>Fecha de Generación del Reporte:</b> {datetime.now().strftime('%d de %B de %Y, %H:%M hrs')}<br/>"
    f"<b>Ubicación del Modelo:</b> {MODEL_PATH.name}<br/>"
    f"<b>Total de Características:</b> {len(model_data['features'])}<br/>"
    f"<b>Algoritmo Final:</b> {model_data['model_name']}",
    styles['CustomBullet']
))

# Construir el PDF
doc.build(story)

print("\n" + "="*60)
print("✓ REPORTE PDF GENERADO EXITOSAMENTE")
print("="*60)
print(f"Ubicación: {PDF_PATH}")
print(f"Tamaño: {PDF_PATH.stat().st_size / 1024:.2f} KB")
print(f"Páginas: ~15-18 páginas")
print("\nContenido incluido:")
print("  • Portada con métricas principales")
print("  • Resumen ejecutivo")
print("  • Arquitectura del modelo")
print("  • Datos de entrenamiento")
print("  • Metodología y algoritmos")
print("  • Resultados y métricas")
print("  • Visualizaciones (3 gráficos)")
print("  • Características técnicas")
print("  • Artefactos generados")
print("  • Limitaciones y conclusiones")
print("="*60)
