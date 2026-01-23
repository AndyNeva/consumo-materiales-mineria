# 📦 Sistema de Gestión y Predicción de Consumo de Materiales

Sistema web integral desarrollado con **Flask**, **SQLite**, **Estructuras de Datos Avanzadas** y **Machine Learning** para el análisis, gestión y predicción del consumo de materiales en plantas de producción de concreto.

Este proyecto implementa algoritmos eficientes de búsqueda (BST y AVL), análisis estadístico automatizado, y modelos de aprendizaje automático para la predicción de demanda de materiales.

---

## 🎯 Características Principales

### 🔍 Búsqueda Eficiente con Estructuras de Datos
- **Árboles Binarios de Búsqueda (BST)**: Implementación clásica para consultas de registros históricos
- **Árboles AVL Auto-balanceados**: Garantiza O(log n) en todas las operaciones
- **Comparación de rendimiento**: Medición en tiempo real de BST vs AVL
- **Búsquedas por rango de fechas**: Optimizadas con poda de subárboles

### 📊 Análisis y Visualización de Datos
- **Gráficas dinámicas con Plotly**: 
  - Volumen por día y por diseño de mezcla
  - Histogramas de distribución de materiales
  - Boxplots de materiales y aditivos
  - Matrices de correlación (heatmaps)
  - Análisis de frecuencia de diseños
- **Dashboard en tiempo real**: Consumo diario, registros recientes, alertas de inventario
- **Exportación de gráficas**: Guardado en alta resolución (300 DPI)

### 🤖 Machine Learning para Predicción
- **Modelos implementados**:
  - Random Forest Regressor
  - Gradient Boosting Regressor
  - XGBoost Regressor
- **Predicción multi-salida**: Arena, Grava y Cemento simultáneamente
- **Features de tiempo avanzadas**:
  - Codificación cíclica (sin/cos) para estacionalidad
  - Variables temporales polinomiales (días, días², días³)
  - Variables de calendario (mes, día del año, semana)
- **Métricas de evaluación**: R², RMSE, MAE, MAPE por material
- **Predicción en lote**: API para múltiples predicciones simultáneas

### 🧹 Limpieza y Preparación de Datos
- **Detección automática de datos faltantes**
- **Validación de datos irracionales**:
  - Valores negativos
  - Humedad fuera de rango (0-100%)
  - Volúmenes inválidos
  - Proporciones cemento/volumen inconsistentes
- **Análisis de outliers con método IQR**:
  - Detección con factor configurable (1.5 o 3.0)
  - Winsorización opcional (reemplazo por límites)
- **Reportes detallados**: Estadísticas de limpieza y datos eliminados

### 🌐 API REST Completa
- **Dashboard**: `/api/dashboard` - Datos principales del sistema
- **Historial**: `/api/historial_consumo` - Búsquedas con BST/AVL
- **Registro**: `/api/despachos` - Alta de despachos con validación
- **Inventario**: `/api/materiales` - Gestión de stock
- **Análisis**: `/api/resumen_consumo` - Agregaciones por rango
- **Gráficas**: `/api/graficas` - Generación dinámica con Plotly
- **Machine Learning**: 
  - `/api/ml/info` - Información del modelo
  - `/api/ml/predecir` - Predicción individual
  - `/api/ml/predecir_batch` - Predicción en lote

---

## 🧰 Tecnologías Utilizadas

### Backend
- **Flask 3.x**: Framework web ligero y flexible
- **SQLite3**: Base de datos relacional embebida
- **Pandas**: Manipulación y análisis de datos
- **NumPy**: Operaciones numéricas y matrices

### Machine Learning
- **Scikit-learn**: Modelos de regresión y preprocesamiento
- **XGBoost**: Gradient Boosting optimizado
- **StandardScaler**: Normalización de features

### Visualización
- **Plotly**: Gráficas interactivas de alta calidad
- **Matplotlib**: Visualizaciones estáticas para análisis

### Estructuras de Datos
- **Implementación propia de BST**: Árbol Binario de Búsqueda
- **Implementación propia de AVL**: Árbol auto-balanceado
- **Patrón de diseño**: Uso de clases abstractas y herencia

---

## 📥 Instalación

### Requisitos Previos

1. **Git** - [Descargar aquí](https://git-scm.com/)
2. **Python 3.10+** - [Descargar aquí](https://www.python.org/downloads/)

Verificar instalación:
```bash
git --version
python --version
```

### Clonar el Repositorio

```bash
git clone https://github.com/AndyNeva/proyecto-consumo-materiales.git
cd proyecto-consumo-materiales
```

⚠️ **Importante**: Nunca descargar como ZIP, siempre usar Git.

### Instalar Dependencias

```bash
pip install -r requirements.txt
```

Dependencias principales:
```
Flask>=3.0.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
plotly>=5.17.0
matplotlib>=3.7.0
openpyxl>=3.1.0
```

---

## 🚀 Configuración Inicial

### 1. Crear Base de Datos

**⚠️ CRÍTICO**: Estos tres scripts deben ejecutarse en orden para crear la base de datos funcional.

```bash
# Paso 1: Crear esquema de base de datos
python database/01_crear_esquema.py

# Paso 2: Cargar datos base (usuarios y materiales)
python database/02_datos_base.py

# Paso 3: Migrar datos históricos desde Excel
python database/03_cargar_datos_iniciales.py
```

**Archivo requerido**: `data/raw/Batch_Plant_Production_2025.xlsm`

**Resultado**: Se crea `db/gestion_materiales.db` con:
- Tabla `usuarios`
- Tabla `materiales` (con inventario)
- Tabla `despachos` (producción histórica)
- Tabla `recetas` (diseños de mezcla)
- Tabla `movimientos` (historial de inventario)
- Tabla `centros_costos` y `zonas`

#### 1.1. Poblar Inventario de Materiales

**⚠️ IMPORTANTE**: Después de crear el esquema, poblar la tabla de materiales con stock inicial.

```bash
# Paso 4: Poblar materiales con inventario inicial
python database/poblar_materiales.py
```

Este script:
- Limpia la tabla `materiales`
- Inserta 12 materiales con stock inicial:
  - Arena, Grava, Cemento, Agua
  - Aditivos: RHEO 1000, Sika 115, BASF 719, Sika 200
  - Aditivos especiales: Delvo, Glenium 7950, Glenium 7970, Fibras
- Configura stock actual, mínimo y máximo para cada material

**Responder 's' cuando pregunte si desea poblar la tabla.**

### 2. Limpiar y Preparar Datos

```bash
python ml/LimpiezaDatos.py
```

Este script:
- Lee `data/raw/Datos_Stat_Model.csv`
- Elimina datos faltantes e irracionales
- Detecta/winsoriza outliers
- Genera `data/processed/DatosLimpios.csv`
- Muestra reporte detallado de limpieza

### 3. Entrenar Modelo de Machine Learning

**⚠️ CRÍTICO**: Este paso es obligatorio para que las predicciones funcionen.

```bash
python ml/MLPFuture.py
```

Este script:
- Entrena modelos Random Forest, Gradient Boosting y XGBoost
- Selecciona el mejor modelo según R² de validación
- Guarda el modelo en `ml/modelo_prediccion.pkl`
- Genera gráficas de evaluación en `ml/graficas/`
- Muestra métricas detalladas por material

**Sin este archivo `.pkl`, la aplicación NO podrá hacer predicciones.**

---

## 🎮 Uso del Sistema

### Iniciar el Servidor

```bash
python app.py
```

El servidor estará disponible en: `http://localhost:5000`

### Credenciales de Acceso

**Login por defecto**:
- **Usuario**: `pteran`
- **Contraseña**: `12345`

### Páginas Web Disponibles

| Ruta | Descripción |
|------|-------------|
| `/login` | Página de inicio de sesión |
| `/dashboard` | Panel principal con métricas |
| `/registro` | Registro de nuevos despachos |
| `/inventario` | Gestión de materiales |
| `/historial` | Búsqueda de registros históricos |
| `/graficas` | Visualización de datos |
| `/ml` | Predicciones con Machine Learning |

---

## 🏗️ Arquitectura del Proyecto

```
proyecto-consumo-materiales/
├── app.py                          # Aplicación Flask principal
├── requirements.txt                # Dependencias Python
│
├── database/                       # Scripts de base de datos
│   ├── 01_crear_esquema.py        # Crea tablas
│   ├── 02_datos_base.py           # Inserta datos iniciales
│   ├── 03_cargar_datos_iniciales.py  # Migra datos históricos
│   └── poblar_materiales.py       # Pobla inventario de materiales
│
├── db/
│   └── gestion_materiales.db      # Base de datos SQLite
│
├── data/
│   ├── raw/                       # Datos originales
│   │   ├── Batch_Plant_Production_2025.xlsm
│   │   └── Datos_Stat_Model.csv
│   └── processed/                 # Datos limpios
│       └── DatosLimpios.csv
│
├── ed/                            # Estructuras de Datos
│   ├── estructuras.py             # BST y AVL implementados
│   └── busquedas.py               # Funciones de búsqueda
│
├── ml/                            # Machine Learning
│   ├── MLPFuture.py               # Entrenamiento del modelo
│   ├── predictor.py               # API de predicción
│   ├── graficas.py                # Generación de gráficas
│   ├── LimpiezaDatos.py           # Limpieza de datos
│   ├── modelo_prediccion.pkl      # Modelo entrenado (generado)
│   └── graficas/                  # Gráficas guardadas
│
├── utils/
│   └── loaders.py                 # Funciones de BD y carga de datos
│
├── templates/                     # Plantillas HTML (frontend)
│   ├── login.html
│   ├── dashboard.html
│   ├── registro.html
│   ├── inventario.html
│   ├── historial.html
│   ├── graficas.html
│   └── ml_prediccion.html
│
└── static/                        # Archivos estáticos (CSS, JS)
    ├── css/
    └── js/
        ├── dashboard.js           # Funciones del dashboard
        ├── graficas.js            # Renderizado de gráficas Plotly
        ├── historial.js           # Búsqueda y filtros de historial
        ├── ml_prediccion.js       # Interfaz de predicciones ML
        └── registro.js            # Formulario de registro de despachos
```

---

## 🔍 Componentes Técnicos Detallados

### Estructuras de Datos: BST y AVL

#### Árbol Binario de Búsqueda (BST)
```python
class ArbolBinarioBusqueda(ArbolBinario):
    """
    Complejidad:
    - Mejor caso (balanceado): O(log n)
    - Peor caso (degenerado): O(n)
    """
```

**Ventajas**: Implementación simple, buena eficiencia en datos aleatorios

**Desventajas**: Puede degenerar a lista enlazada con datos ordenados

#### Árbol AVL
```python
class ArbolAVL(ArbolBinario):
    """
    Complejidad garantizada: O(log n)
    Auto-balanceo con rotaciones
    """
```

**Ventajas**: Rendimiento garantizado, ideal para datos ordenados

**Características**:
- Factor de balance: altura(izq) - altura(der)
- Rotaciones simples (derecha/izquierda)
- Rotaciones dobles (izq-der, der-izq)

### Machine Learning: Flujo de Trabajo

1. **Carga de datos limpios**
   ```python
   df = pd.read_csv('data/processed/DatosLimpios.csv')
   ```

2. **Ingeniería de features**
   - Conversión de fechas a días numéricos
   - Variables polinomiales: días, días², días³
   - Codificación cíclica: sin(2π·mes/12), cos(2π·mes/12)
   - One-hot encoding de diseños top

3. **División y escalado**
   ```python
   X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
   scaler_X = StandardScaler().fit(X_train)
   scaler_y = StandardScaler().fit(y_train)
   ```

4. **Entrenamiento de modelos**
   ```python
   modelos = {
       'Random Forest': MultiOutputRegressor(RandomForestRegressor(...)),
       'Gradient Boosting': MultiOutputRegressor(GradientBoostingRegressor(...)),
       'XGBoost': MultiOutputRegressor(XGBRegressor(...))
   }
   ```

5. **Selección del mejor modelo**
   ```python
   mejor_modelo = max(resultados, key=lambda k: resultados[k]['r2_test'])
   ```

6. **Serialización**
   ```python
   with open('modelo_prediccion.pkl', 'wb') as f:
       pickle.dump({
           'modelo': mejor_modelo,
           'scaler_X': scaler_X,
           'scaler_y': scaler_y,
           'metricas': {...}
       }, f)
   ```

### API de Predicción

Para ejemplos detallados de uso de todas las APIs, consultar el documento **`API_DOCUMENTATION.md`**.

---

## 📊 Ejemplo de Búsqueda con Estructuras de Datos

```python
from ed.busquedas import buscar_por_rango

# Búsqueda con BST y AVL (comparación automática)
resultados, tiempo_bst, tiempo_avl = buscar_por_rango('2025-01-01', '2025-12-31')

print(f"BST: {len(resultados)} registros en {tiempo_bst*1000:.4f}ms")
print(f"AVL: {len(resultados)} registros en {tiempo_avl*1000:.4f}ms")
```

**Salida típica**:
```
Búsqueda '2025-01-01' a '2025-12-31':
  BST: 1250 registros en 2.3451ms (0.002345s)
  AVL: 1250 registros en 1.8762ms (0.001876s)
```

---

## 📝 Documentación de APIs

Para documentación detallada de todos los endpoints, consultar:

**`API_DOCUMENTATION.md`**

Incluye:
- Especificación completa de cada endpoint
- Parámetros requeridos y opcionales
- Ejemplos de request/response
- Códigos de estado HTTP
- Ejemplos con cURL y Python

---

## 🧪 Testing

### Probar el Modelo de ML
```bash
python ml/MLPFuture.py
```

Verifica:
- ✅ R² > 0.90 (alta precisión)
- ✅ RMSE razonable según escala de datos
- ✅ Gráficas generadas en `ml/graficas/`

### Probar Búsquedas
```bash
python -c "from ed.busquedas import buscar_por_rango; buscar_por_rango('2025-01-01', '2025-12-31')"
```

### Probar API
```bash
# Iniciar servidor
python app.py

# En otra terminal
curl http://localhost:5000/api/dashboard
```

---

## 🐛 Solución de Problemas

### Error: "Modelo no encontrado"
**Causa**: No se ejecutó `ml/MLPFuture.py`

**Solución**:
```bash
python ml/MLPFuture.py
```

### Error: "No such table: despachos"
**Causa**: No se creó la base de datos

**Solución**:
```bash
python database/01_crear_esquema.py
python database/02_datos_base.py
python database/03_cargar_datos_iniciales.py
```

### Error: "FileNotFoundError: DatosLimpios.csv"
**Causa**: No se ejecutó el script de limpieza

**Solución**:
```bash
python ml/LimpiezaDatos.py
```

### Error: Inventario vacío o materiales faltantes
**Causa**: No se ejecutó `poblar_materiales.py`

**Solución**:
```bash
python database/poblar_materiales.py
```
Responder 's' cuando pregunte.

### Error: Recursión excedida en árboles
**Causa**: Árbol muy grande

**Solución**: Ya configurado en `busquedas.py`:
```python
import sys
sys.setrecursionlimit(10000)
```

---

## 📄 Licencia

Este proyecto es de uso académico para el curso de Estructuras de Datos y Machine Learning.

---

## 👥 Equipo de Desarrollo

- **Frontend**: HTML/CSS
- **JavaScript**: Integración y lógica de cliente
- **Backend**: Flask y Estructuras de Datos
- **Database**: SQLite y migraciones
- **Machine Learning**: Modelos predictivos

---

## 📚 Referencias

- [Documentación Flask](https://flask.palletsprojects.com/)
- [Scikit-learn](https://scikit-learn.org/)
- [Plotly Python](https://plotly.com/python/)
- [XGBoost](https://xgboost.readthedocs.io/)

---

## 🔮 Roadmap Futuro

- [ ] Implementación de autenticación de usuarios
- [ ] Dashboard de administración de roles
- [ ] Exportación de reportes a PDF
- [ ] Sistema de alertas automáticas por email
- [ ] Integración con proveedores externos
- [ ] App móvil para registro de despachos
- [ ] Modelos LSTM para series de tiempo
- [ ] API GraphQL

---
