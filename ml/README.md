# 📊 Módulo de Machine Learning y Estadísticas

Este módulo contiene scripts para análisis estadístico y visualización de datos del proyecto de gestión de materiales.

## Archivos

### 📈 `estadisticas.py`
Script principal que calcula y muestra estadísticos del dataset de despachos.

**Características:**
- Carga datos desde la base de datos SQLite
- Calcula 10 estadísticos diferentes
- Muestra información detallada en consola
- Opción interactiva para visualizar gráficas

**Uso:**
```bash
python ml/estadisticas.py
```

El script te preguntará si deseas ver las gráficas al finalizar.

### 📊 `visualizar_graficas.py`
Script dedicado para generar automáticamente todas las visualizaciones en ventanas emergentes.

**Características:**
- Genera 10 gráficas en ventanas emergentes
- Cada gráfica se muestra secuencialmente
- No requiere interacción previa

**Uso:**
```bash
python ml/visualizar_graficas.py
```

### 💾 `exportar_graficas.py`
Script para exportar todas las gráficas como archivos PNG.

**Características:**
- Genera 10 gráficas y las guarda en archivos
- Crea el directorio `ml/graficas/` automáticamente
- Alta calidad (150 DPI)
- No abre ventanas emergentes

**Uso:**
```bash
python ml/exportar_graficas.py
```

Las gráficas se guardarán en: `ml/graficas/`

## Estadísticos Calculados

1. **Volumen Promedio por Zona** (Top 15)
   - Gráfico de barras verticales
   - Muestra las zonas con mayor volumen promedio de despacho

2. **Despachos por Turno**
   - Gráfico de pastel
   - Distribución porcentual de despachos por turno (DIA/NOCHE)

3. **Asentamiento Promedio por Fuente de Cemento**
   - Gráfico de barras
   - Comparación entre diferentes fuentes de cemento

4. **Humedad de Arena Promedio por Zona** (Top 20)
   - Gráfico de barras horizontales
   - Zonas con mayor humedad de arena

5. **Temperatura Promedio por Turno**
   - Gráfico de barras con línea de media
   - Temperatura ambiente durante los despachos

6. **Despachos por Lote** (Top 10)
   - Gráfico de barras
   - Lotes con mayor cantidad de despachos

7. **Volumen Total por Diseño de Mezcla** (Top 15)
   - Gráfico de barras horizontales
   - Diseños de mezcla más utilizados

8. **Asentamiento por Diseño de Mezcla** (Top 15)
   - Gráfico de barras
   - Asentamiento promedio según diseño

9. **Despachos por WBS** (Top 10)
   - Gráfico de barras
   - Centros de costo con más despachos

10. **Correlación Volumen vs Asentamiento**
    - Visualización numérica con indicador de fuerza
    - Muestra la relación entre volumen y asentamiento

## Requisitos

```bash
pandas
matplotlib
seaborn
sqlite3 (incluido en Python)
```

## Notas

- Las gráficas se muestran en ventanas emergentes secuencialmente
- Cierra cada ventana para ver la siguiente gráfica
- Los datos se cargan desde `db/gestion_materiales.db`
- Se requiere que la base de datos esté inicializada con datos

## Próximos Pasos

- [ ] Agregar modelos de predicción
- [ ] Implementar análisis de series temporales
- [ ] Crear dashboard interactivo
- [ ] Exportar gráficas a PDF/PNG
