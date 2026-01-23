# 📡 Documentación de APIs - Sistema de Gestión de Materiales

Esta documentación describe todos los endpoints REST disponibles en el sistema de gestión y predicción de consumo de materiales.

**URL Base**: `http://localhost:5000`

---

## 📋 Índice

### APIs de Datos Generales
1. [Dashboard](#1-dashboard) - Datos principales del sistema
2. [Recetas](#2-recetas) - Listado de diseños de mezcla

### APIs de Despachos y Producción
3. [Registro de Despachos](#3-registro-de-despachos) - Alta de producción
4. [Historial de Consumo](#4-historial-de-consumo) - Búsqueda con BST/AVL
5. [Resumen de Consumo](#5-resumen-de-consumo) - Agregaciones por periodo

### APIs de Inventario
6. [Gestión de Materiales](#6-gestión-de-materiales) - CRUD de inventario
7. [Cruce Consumo vs Stock](#7-cruce-consumo-vs-stock) - Validación pre-registro

### APIs de Análisis
8. [Gráficas Dinámicas](#8-gráficas-dinámicas) - Visualizaciones con Plotly

### APIs de Machine Learning
9. [Información del Modelo](#9-información-del-modelo) - Métricas y detalles
10. [Predicción Individual](#10-predicción-individual) - Predicción de materiales
11. [Predicción en Lote](#11-predicción-en-lote) - Múltiples predicciones

---

## 1. Dashboard

### `GET /api/dashboard`

Obtiene los datos principales para el dashboard del sistema: consumo diario, registros recientes e inventario.

#### Request
No requiere parámetros.

#### Response Success (200 OK)
```json
{
  "consumo_diario": 125.5,
  "registros_ultima_semana": [
    {
      "fecha": "2026-01-12",
      "diseno_mezcla": "H-210-45-19-G",
      "zona": "Zona Norte",
      "wbs": "WBS-001",
      "volumen_m3": 15.5
    }
  ],
  "cantidad_registros_semana": 42,
  "inventario": [
    {
      "material": "Cemento",
      "unidad": "Kg",
      "stock": 50000,
      "minimo": 10000
    },
    {
      "material": "Arena",
      "unidad": "Kg",
      "stock": 4500,
      "minimo": 5000
    }
  ]
}
```

#### Ejemplo con cURL
```bash
curl -X GET http://localhost:5000/api/dashboard
```

#### Ejemplo con Python
```python
import requests
response = requests.get('http://localhost:5000/api/dashboard')
data = response.json()
print(f"Consumo hoy: {data['consumo_diario']} m³")
```

---

## 2. Recetas

### `GET /api/recetas`

Obtiene la lista de diseños de mezcla disponibles en el sistema.

#### Request
No requiere parámetros.

#### Response Success (200 OK)
```json
{
  "ok": true,
  "disenos": [
    "H-210-45-19-G",
    "H-280-45-19-G",
    "H-350-45-19-G",
    "H-175-45-19-G"
  ]
}
```

#### Ejemplo con cURL
```bash
curl -X GET http://localhost:5000/api/recetas
```

---

## 3. Registro de Despachos

### `POST /api/despachos`

Registra un nuevo despacho de producción y actualiza automáticamente el inventario de materiales.

#### Request Body
```json
{
  "fecha": "2026-01-23",
  "volumen_m3": 6.5,
  "diseno_mezcla": "H-210-45-19-G",
  "zona": "Zona Norte",
  "wbs": "WBS-001",
  "turno": "Diurno",
  "arena_humedad_pct": 3.5,
  "asentamiento_final_cm": 18.0,
  "temperatura_c": 25.0
}
```

#### Campos del Request

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `fecha` | string | Sí | Fecha del despacho (YYYY-MM-DD) |
| `volumen_m3` | number | Sí | Volumen producido en m³ |
| `diseno_mezcla` | string | Sí | Código del diseño de mezcla |
| `zona` | string | Sí | Zona de destino |
| `wbs` | string | Sí | Código WBS del proyecto |
| `turno` | string | Sí | Turno de producción (Diurno/Nocturno) |
| `arena_humedad_pct` | number | Sí | Humedad de arena en % (0-100) |
| `asentamiento_final_cm` | number | Sí | Asentamiento en cm (≥0) |
| `temperatura_c` | number | Sí | Temperatura en °C |

#### Response Success (200 OK)
```json
{
  "ok": true,
  "id": 1234
}
```

#### Response Error (400 Bad Request)
```json
{
  "ok": false,
  "error": "No se pudo insertar el despacho (revisa validaciones/receta/BD)."
}
```

#### Validaciones Automáticas
- ✅ Verifica que exista la receta del diseño de mezcla
- ✅ Calcula consumos automáticamente según receta
- ✅ Descuenta stock de materiales del inventario
- ✅ Valida volumen > 0

#### Ejemplo con cURL
```bash
curl -X POST http://localhost:5000/api/despachos \
  -H "Content-Type: application/json" \
  -d '{
    "fecha": "2026-01-23",
    "volumen_m3": 6.5,
    "diseno_mezcla": "H-210-45-19-G",
    "zona": "Zona Norte",
    "wbs": "WBS-001",
    "turno": "Diurno",
    "arena_humedad_pct": 3.5,
    "asentamiento_final_cm": 18.0,
    "temperatura_c": 25.0
  }'
```

#### Ejemplo con Python
```python
import requests

despacho = {
    "fecha": "2026-01-23",
    "volumen_m3": 6.5,
    "diseno_mezcla": "H-210-45-19-G",
    "zona": "Zona Norte",
    "wbs": "WBS-001",
    "turno": "Diurno",
    "arena_humedad_pct": 3.5,
    "asentamiento_final_cm": 18.0,
    "temperatura_c": 25.0
}

response = requests.post('http://localhost:5000/api/despachos', json=despacho)
if response.json()['ok']:
    print(f"Despacho registrado con ID: {response.json()['id']}")
```

---

## 4. Historial de Consumo

### `GET /api/historial_consumo`

Obtiene el historial de despachos utilizando **estructuras de datos BST y AVL** para búsquedas eficientes. Retorna tiempos de ejecución de ambos algoritmos para comparación.

#### Request Parameters

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `inicio` | string | **Sí** | Fecha inicial (YYYY-MM-DD) |
| `fin` | string | **Sí** | Fecha final (YYYY-MM-DD) |
| `diseno` | string | No | Filtro por diseño de mezcla |
| `zona` | string | No | Filtro por zona (búsqueda parcial) |
| `turno` | string | No | Filtro por turno |
| `wbs` | string | No | Filtro por WBS (búsqueda parcial) |

#### Response Success (200 OK)
```json
{
  "datos": [
    {
      "id": 1,
      "fecha": "2025-06-15",
      "diseno": "H-210-45-19-G",
      "zona": "Zona Norte",
      "wbs": "WBS-001",
      "turno": "Diurno",
      "volumen_m3": 15.5,
      "arena_kg": 12400.0,
      "grava_kg": 13950.0,
      "cemento_kg": 5425.0,
      "agua_kg": 2712.5,
      "aditivo_rheo_sika115": 0.0,
      "aditivo_basf_sika200": 15.5,
      "aditivo_delvo": 0.0,
      "aditivo_glenium_7950": 0.0,
      "aditivo_glenium_7970": 0.0,
      "aditivo_fibras": 0.0,
      "arena_humedad_pct": 3.5,
      "asentamiento_final_cm": 18.0,
      "temperatura_c": 25.0
    }
  ],
  "tiempos": {
    "bst": 0.002345,
    "avl": 0.001876
  },
  "total": 150
}
```

#### Response Error (400 Bad Request)
```json
{
  "error": "Debes enviar 'inicio' y 'fin'."
}
```

#### Características Especiales
- 🌲 **Búsqueda con BST**: Árbol binario de búsqueda simple
- 🌲 **Búsqueda con AVL**: Árbol auto-balanceado (más eficiente)
- ⚡ **Comparación de rendimiento**: Retorna tiempos de ejecución
- 🔍 **Filtros combinados**: Permite múltiples filtros simultáneos

#### Ejemplo con cURL
```bash
# Búsqueda simple por rango
curl -X GET "http://localhost:5000/api/historial_consumo?inicio=2025-01-01&fin=2025-12-31"

# Búsqueda con filtros
curl -X GET "http://localhost:5000/api/historial_consumo?inicio=2025-01-01&fin=2025-12-31&diseno=H-210-45-19-G&zona=Norte&turno=Diurno"
```

#### Ejemplo con Python
```python
import requests

params = {
    "inicio": "2025-01-01",
    "fin": "2025-12-31",
    "diseno": "H-210-45-19-G",
    "zona": "Norte"
}

response = requests.get('http://localhost:5000/api/historial_consumo', params=params)
data = response.json()

print(f"Total de registros: {data['total']}")
print(f"Tiempo BST: {data['tiempos']['bst']*1000:.2f} ms")
print(f"Tiempo AVL: {data['tiempos']['avl']*1000:.2f} ms")
print(f"AVL es {data['tiempos']['bst']/data['tiempos']['avl']:.2f}x más rápido")
```

---

## 5. Resumen de Consumo

### `GET /api/resumen_consumo`

Obtiene totales agregados de consumo de materiales en un rango de fechas, con filtros opcionales.

#### Request Parameters

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `inicio` | string | **Sí** | Fecha inicial (YYYY-MM-DD) |
| `fin` | string | **Sí** | Fecha final (YYYY-MM-DD) |
| `diseno` | string | No | Filtro por diseño |
| `zona` | string | No | Filtro por zona |
| `turno` | string | No | Filtro por turno |
| `wbs` | string | No | Filtro por WBS |

#### Response Success (200 OK)
```json
{
  "ok": true,
  "resumen": {
    "registros": 150,
    "volumen_m3": 975.0,
    "arena_kg": 780000.0,
    "grava_kg": 877500.0,
    "cemento_kg": 341250.0,
    "agua_kg": 170625.0,
    "aditivo_rheo_sika115": 0.0,
    "aditivo_basf_sika200": 975.0,
    "aditivo_delvo": 0.0,
    "aditivo_glenium_7950": 0.0,
    "aditivo_glenium_7970": 0.0,
    "aditivo_fibras": 0.0
  }
}
```

#### Ejemplo con cURL
```bash
curl -X GET "http://localhost:5000/api/resumen_consumo?inicio=2025-01-01&fin=2025-12-31&diseno=H-210-45-19-G"
```

---

## 6. Gestión de Materiales

### `GET /api/materiales`

Obtiene la lista completa de materiales con su inventario actual.

#### Response Success (200 OK)
```json
{
  "ok": true,
  "materiales": [
    {
      "id": 1,
      "nombre": "Cemento",
      "unidad": "Kg",
      "stock_actual": 50000.0,
      "stock_minimo": 10000.0,
      "stock_maximo": 100000.0
    },
    {
      "id": 2,
      "nombre": "Arena",
      "unidad": "Kg",
      "stock_actual": 4500.0,
      "stock_minimo": 5000.0,
      "stock_maximo": 50000.0
    }
  ]
}
```

### `POST /api/materiales`

Actualiza el stock de un material existente.

#### Request Body
```json
{
  "id": 1,
  "stock_actual": 55000.0,
  "stock_minimo": 12000.0
}
```

#### Campos del Request

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id` | number | **Sí** | ID del material |
| `stock_actual` | number | No | Nuevo stock actual |
| `stock_minimo` | number | No | Nuevo stock mínimo |

#### Response Success (200 OK)
```json
{
  "ok": true,
  "mensaje": "Material actualizado"
}
```

#### Response Error (404 Not Found)
```json
{
  "ok": false,
  "error": "Material no encontrado"
}
```

#### Ejemplo con Python
```python
import requests

# Obtener lista de materiales
response = requests.get('http://localhost:5000/api/materiales')
materiales = response.json()['materiales']

# Actualizar stock de cemento
actualizar = {
    "id": 1,
    "stock_actual": 55000.0,
    "stock_minimo": 12000.0
}
response = requests.post('http://localhost:5000/api/materiales', json=actualizar)
```

---

## 7. Cruce Consumo vs Stock

### `POST /api/cruce_consumo_registro`

Calcula el cruce entre consumo estimado y stock disponible para validar si es posible realizar un despacho **sin registrarlo**.

#### Request Body
```json
{
  "diseno_mezcla": "H-210-45-19-G",
  "volumen_m3": 6.5
}
```

#### Campos del Request

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `diseno_mezcla` | string | **Sí** | Código del diseño |
| `volumen_m3` | number | **Sí** | Volumen a producir |

#### Response Success (200 OK)
```json
{
  "ok": true,
  "datos": [
    {
      "material": "Cemento",
      "unidad": "kg",
      "stock_actual": 50000.0,
      "minimo": 10000.0,
      "consumo_estimado": 2275.0,
      "saldo": 47725.0,
      "bajo_minimo": false,
      "estado": "OK"
    },
    {
      "material": "Arena",
      "unidad": "kg",
      "stock_actual": 4500.0,
      "minimo": 5000.0,
      "consumo_estimado": 5200.0,
      "saldo": -700.0,
      "bajo_minimo": true,
      "estado": "Deficit"
    }
  ],
  "no_mapeados": [],
  "no_encontrados": []
}
```

#### Estados Posibles

| Estado | Descripción |
|--------|-------------|
| `"OK"` | Stock suficiente y por encima del mínimo |
| `"Bajo minimo"` | Stock suficiente pero por debajo del mínimo |
| `"Deficit"` | Stock insuficiente (saldo negativo) |

#### Ejemplo con cURL
```bash
curl -X POST http://localhost:5000/api/cruce_consumo_registro \
  -H "Content-Type: application/json" \
  -d '{"diseno_mezcla": "H-210-45-19-G", "volumen_m3": 6.5}'
```

#### Ejemplo con Python
```python
import requests

datos = {
    "diseno_mezcla": "H-210-45-19-G",
    "volumen_m3": 6.5
}

response = requests.post('http://localhost:5000/api/cruce_consumo_registro', json=datos)
cruce = response.json()['datos']

for material in cruce:
    if material['estado'] == 'Deficit':
        print(f"⚠️ {material['material']}: Falta {abs(material['saldo']):.2f} {material['unidad']}")
    elif material['estado'] == 'Bajo minimo':
        print(f"⚡ {material['material']}: Stock bajo mínimo")
    else:
        print(f"✅ {material['material']}: OK")
```

---

## 8. Gráficas Dinámicas

### `GET /api/graficas`

Genera gráficas interactivas con Plotly basadas en los datos filtrados.

#### Request Parameters

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `inicio` | string | **Sí** | Fecha inicial (YYYY-MM-DD) |
| `fin` | string | **Sí** | Fecha final (YYYY-MM-DD) |
| `diseno` | string | No | Filtro por diseño |
| `zona` | string | No | Filtro por zona |
| `turno` | string | No | Filtro por turno |
| `wbs` | string | No | Filtro por WBS |

#### Response Success (200 OK)
```json
{
  "ok": true,
  "graficas": [
    {
      "nombre": "volumen_por_dia",
      "figura": {
        "data": [...],
        "layout": {...}
      }
    },
    {
      "nombre": "volumen_por_diseno",
      "figura": {
        "data": [...],
        "layout": {...}
      }
    },
    {
      "nombre": "boxplot_materiales",
      "figura": {
        "data": [...],
        "layout": {...}
      }
    }
  ],
  "num_registros": 150
}
```

#### Tipos de Gráficas Disponibles

| Nombre | Descripción |
|--------|-------------|
| `volumen_por_dia` | Barras de volumen diario |
| `volumen_por_diseno` | Barras de volumen por diseño |
| `hist_volumen` | Histograma de distribución de volumen |
| `hist_aditivos` | Histograma de aditivos |
| `frecuencia_diseno` | Frecuencia de diseños utilizados |
| `boxplot_materiales` | Boxplot de materiales principales |
| `boxplot_aditivos` | Boxplot de aditivos |
| `corr_materiales` | Heatmap de correlación de materiales |
| `corr_aditivos` | Heatmap de correlación de aditivos |

#### Ejemplo con cURL
```bash
curl -X GET "http://localhost:5000/api/graficas?inicio=2025-01-01&fin=2025-12-31"
```

#### Ejemplo con Python
```python
import requests
import plotly.graph_objects as go

response = requests.get('http://localhost:5000/api/graficas', params={
    "inicio": "2025-01-01",
    "fin": "2025-12-31"
})

graficas = response.json()['graficas']

# Renderizar primera gráfica
primera = graficas[0]
fig = go.Figure(primera['figura'])
fig.show()
```

---

## 9. Información del Modelo

### `GET /api/ml/info`

Obtiene información detallada del modelo de Machine Learning entrenado.

#### Response Success (200 OK)
```json
{
  "modelo_tipo": "XGBoost",
  "fecha_entrenamiento": "2026-01-15",
  "metricas_globales": {
    "r2_test": 0.9456,
    "rmse_test": 125.34,
    "mae_test": 89.67,
    "mse_train": 8234.56,
    "mse_test": 15710.27
  },
  "metricas_por_material": {
    "Arena (kg)": {
      "r2": 0.9523,
      "mae": 78.45,
      "rmse": 112.34,
      "mape": 5.67
    },
    "Grava (kg)": {
      "r2": 0.9412,
      "mae": 92.34,
      "rmse": 128.67,
      "mape": 6.12
    },
    "Cemento (kg)": {
      "r2": 0.9434,
      "mae": 45.23,
      "rmse": 89.56,
      "mape": 4.89
    }
  },
  "variables_predictoras": [
    "FECHA_NUMERICO",
    "FECHA_NUMERICO_SQ",
    "FECHA_NUMERICO_CU",
    "MES_SIN",
    "MES_COS",
    "TURNO_BIN",
    "Volumen (m3)",
    "DISENO_H-210-45-19-G",
    "DISENO_H-280-45-19-G"
  ],
  "targets": ["Arena (kg)", "Grava (kg)", "Cemento (kg)"]
}
```

#### Response Error (404 Not Found)
```json
{
  "error": "Modelo no encontrado",
  "detalle": "Ejecuta primero ml/MLPFuture.py para entrenar el modelo"
}
```

#### Ejemplo con cURL
```bash
curl -X GET http://localhost:5000/api/ml/info
```

---

## 10. Predicción Individual

### `POST /api/ml/predecir`

Realiza una predicción de consumo de materiales para una fecha futura específica.

#### Request Body
```json
{
  "fecha": "2026-02-15",
  "turno": "DIA",
  "diseno": "H-210-45-19-G",
  "volumen": 6.5
}
```

#### Campos del Request

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `fecha` | string | **Sí** | Fecha de predicción (YYYY-MM-DD) |
| `turno` | string | No | Turno (DIA/NOCHE, default: DIA) |
| `diseno` | string | No | Diseño de mezcla (default: OTROS) |
| `volumen` | number | No | Volumen en m³ (default: 6.0) |

#### Response Success (200 OK)
```json
{
  "fecha": "2026-02-15",
  "Arena (kg)": 5134.67,
  "Grava (kg)": 5850.23,
  "Cemento (kg)": 2275.45
}
```

#### Response Error (400 Bad Request)
```json
{
  "error": "El campo 'fecha' es requerido"
}
```

#### Ejemplo con cURL
```bash
curl -X POST http://localhost:5000/api/ml/predecir \
  -H "Content-Type: application/json" \
  -d '{
    "fecha": "2026-02-15",
    "turno": "DIA",
    "diseno": "H-210-45-19-G",
    "volumen": 6.5
  }'
```

#### Ejemplo con Python
```python
import requests

prediccion = {
    "fecha": "2026-02-15",
    "turno": "DIA",
    "diseno": "H-210-45-19-G",
    "volumen": 6.5
}

response = requests.post('http://localhost:5000/api/ml/predecir', json=prediccion)
resultado = response.json()

print(f"Predicción para {resultado['fecha']}:")
print(f"  Arena:   {resultado['Arena (kg)']:>10,.2f} kg")
print(f"  Grava:   {resultado['Grava (kg)']:>10,.2f} kg")
print(f"  Cemento: {resultado['Cemento (kg)']:>10,.2f} kg")
```

---

## 11. Predicción en Lote

### `POST /api/ml/predecir_batch`

Realiza múltiples predicciones en una sola petición.

#### Request Body
```json
{
  "predicciones": [
    {
      "fecha": "2026-02-01",
      "turno": "DIA",
      "diseno": "H-210-45-19-G",
      "volumen": 5.0
    },
    {
      "fecha": "2026-02-02",
      "turno": "NOCHE",
      "diseno": "H-280-45-19-G",
      "volumen": 8.0
    },
    {
      "fecha": "2026-02-03",
      "turno": "DIA",
      "diseno": "H-210-45-19-G",
      "volumen": 6.0
    }
  ]
}
```

#### Response Success (200 OK)
```json
{
  "predicciones": [
    {
      "fecha": "2026-02-01",
      "Arena (kg)": 4278.90,
      "Grava (kg)": 4875.12,
      "Cemento (kg)": 1896.34
    },
    {
      "fecha": "2026-02-02",
      "Arena (kg)": 6846.23,
      "Grava (kg)": 7800.45,
      "Cemento (kg)": 3034.67
    },
    {
      "fecha": "2026-02-03",
      "Arena (kg)": 5134.67,
      "Grava (kg)": 5850.23,
      "Cemento (kg)": 2275.45
    }
  ],
  "total": 3
}
```

#### Ejemplo con cURL
```bash
curl -X POST http://localhost:5000/api/ml/predecir_batch \
  -H "Content-Type: application/json" \
  -d '{
    "predicciones": [
      {"fecha": "2026-02-01", "turno": "DIA", "diseno": "H-210", "volumen": 5},
      {"fecha": "2026-02-02", "turno": "NOCHE", "diseno": "H-280", "volumen": 8}
    ]
  }'
```

#### Ejemplo con Python
```python
import requests
import pandas as pd

# Crear múltiples predicciones
fechas = pd.date_range('2026-02-01', '2026-02-07', freq='D')
predicciones = []

for fecha in fechas:
    predicciones.append({
        "fecha": fecha.strftime('%Y-%m-%d'),
        "turno": "DIA",
        "diseno": "H-210-45-19-G",
        "volumen": 6.0
    })

# Enviar batch
response = requests.post('http://localhost:5000/api/ml/predecir_batch', json={
    "predicciones": predicciones
})

resultados = response.json()['predicciones']

# Convertir a DataFrame
df = pd.DataFrame(resultados)
print(df)

# Totales por material
print("\nTotales semanales:")
print(f"Arena:   {df['Arena (kg)'].sum():,.2f} kg")
print(f"Grava:   {df['Grava (kg)'].sum():,.2f} kg")
print(f"Cemento: {df['Cemento (kg)'].sum():,.2f} kg")
```

---

## 📌 Notas Técnicas

### Headers Requeridos
Todas las peticiones POST deben incluir:
```
Content-Type: application/json
```

### Formato de Fechas
Todas las fechas siguen el formato ISO 8601: `YYYY-MM-DD`

Ejemplos válidos:
- `2026-01-23`
- `2025-12-31`
- `2026-02-01`

### Codificación
Todas las respuestas usan `charset=utf-8` con `ensure_ascii=False` para soportar caracteres especiales y tildes.

### Manejo de Errores
Todos los endpoints capturan excepciones y retornan:
```json
{
  "error": "Descripción del error",
  "detalle": "Información adicional (opcional)"
}
```

### CORS
El servidor actualmente **no tiene** configuración CORS. Para entornos de producción que requieran acceso desde otros dominios, agregar:

```python
from flask_cors import CORS
CORS(app)
```

---

## 🔐 Autenticación

Actualmente el sistema **no requiere autenticación** para las APIs. Todas las peticiones son públicas.

Para producción se recomienda implementar:
- JWT (JSON Web Tokens)
- API Keys
- OAuth 2.0

---

## 📊 Códigos de Estado HTTP

| Código | Descripción | Uso |
|--------|-------------|-----|
| `200 OK` | Petición exitosa | GET, cálculos completados |
| `201 Created` | Recurso creado | POST exitoso de registro |
| `400 Bad Request` | Petición inválida | Parámetros faltantes, valores inválidos |
| `404 Not Found` | Recurso no encontrado | Material/receta inexistente |
| `500 Internal Server Error` | Error del servidor | Errores de BD, excepciones |

---

## 🧪 Testing de APIs

### Colección Postman

Para facilitar el testing, se puede crear una colección de Postman con todos los endpoints.

### Ejemplo de Script de Testing

```python
import requests
import json

BASE_URL = "http://localhost:5000"

def test_dashboard():
    response = requests.get(f"{BASE_URL}/api/dashboard")
    assert response.status_code == 200
    assert 'consumo_diario' in response.json()
    print("✅ Dashboard OK")

def test_historial():
    params = {"inicio": "2025-01-01", "fin": "2025-12-31"}
    response = requests.get(f"{BASE_URL}/api/historial_consumo", params=params)
    assert response.status_code == 200
    assert 'tiempos' in response.json()
    assert 'bst' in response.json()['tiempos']
    assert 'avl' in response.json()['tiempos']
    print("✅ Historial OK")

def test_prediccion():
    data = {
        "fecha": "2026-02-15",
        "turno": "DIA",
        "diseno": "H-210-45-19-G",
        "volumen": 6.0
    }
    response = requests.post(f"{BASE_URL}/api/ml/predecir", json=data)
    assert response.status_code == 200
    assert 'Arena (kg)' in response.json()
    print("✅ Predicción OK")

if __name__ == "__main__":
    test_dashboard()
    test_historial()
    test_prediccion()
    print("\n🎉 Todas las pruebas pasaron exitosamente")
```

---

## 🚀 Mejores Prácticas

### 1. Manejo de Errores
Siempre verificar el código de estado antes de procesar la respuesta:

```python
response = requests.get('http://localhost:5000/api/dashboard')
if response.status_code == 200:
    data = response.json()
    # Procesar datos
else:
    print(f"Error: {response.status_code}")
    print(response.json().get('error', 'Error desconocido'))
```

### 2. Timeout en Peticiones
Siempre usar timeout para evitar bloqueos:

```python
response = requests.get('http://localhost:5000/api/historial_consumo', 
                       params={"inicio": "2025-01-01", "fin": "2025-12-31"},
                       timeout=10)
```

### 3. Validación de Datos
Validar datos antes de enviar:

```python
from datetime import datetime

def validar_fecha(fecha_str):
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

fecha = "2026-02-15"
if validar_fecha(fecha):
    # Hacer petición
    pass
```

---

**Última actualización**: Enero 2026  
**Versión de la API**: 1.0