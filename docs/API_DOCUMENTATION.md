# Documentación de APIs - Sistema de Gestión de Materiales

## Índice
1. [API Dashboard](#api-dashboard)
2. [API Historial](#api-historial)
3. [API Consumos](#api-consumos)
4. [API Registro](#api-registro)
5. [API Estado de Materiales](#api-estado-de-materiales)
6. [API Agregar Material](#api-agregar-material)

---

## API Dashboard

### `GET /api/dashboard`

Obtiene los datos principales para el dashboard del sistema.

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
  "alertas_inventario": [
    {
      "material": "Cemento",
      "stock": 50000,
      "minimo": 10000,
      "estado": "ok"
    },
    {
      "material": "Arena",
      "stock": 4500,
      "minimo": 5000,
      "estado": "bajo"
    }
  ],
  "cantidad_alertas_inventario": 3
}
```

#### Códigos de Estado
- `200 OK`: Datos obtenidos exitosamente

---

## API Historial

### `GET /api/historial`

Obtiene el historial de despachos filtrado por fecha y opcionalmente por diseño de mezcla y zona.

#### Request Parameters
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `inicio` | string | Sí | Fecha inicial (formato: YYYY-MM-DD) |
| `fin` | string | Sí | Fecha final (formato: YYYY-MM-DD) |
| `diseno` | string | No | Código del diseño de mezcla |
| `zona` | string | No | Nombre de la zona |

#### Ejemplo de Request
```
GET /api/historial?inicio=2025-01-01&fin=2025-12-31&diseno=H-210-45-19-G&zona=Zona Norte
```

#### Response Success (200 OK)
```json
{
  "datos": [
    {
      "id": 1,
      "fecha": "2025-06-15",
      "fuente_cemento": "DIS_LI744",
      "diseno_mezcla": "H-210-45-19-G",
      "lote": "123",
      "zona": "Zona Norte",
      "wbs": "WBS-001",
      "volumen_m3": 15.5,
      "turno": "Diurno",
      "arena_humedad_pct": 3.5,
      "asentamiento_final_cm": 18.0,
      "temperatura_c": 25.0,
      "cemento_kg": 350.0,
      "arena_kg": 800.0,
      "grava_kg": 900.0,
      "agua_kg": 175.0
    }
  ],
  "tiempos": {
    "bst": 0.002345,
    "avl": 0.001234
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

#### Códigos de Estado
- `200 OK`: Búsqueda exitosa
- `400 Bad Request`: Faltan parámetros requeridos

---

## API Consumos

### `POST /api/consumos`

Calcula los consumos de materiales para un diseño de mezcla y volumen específico, sin registrar el despacho.

#### Request Body
```json
{
  "diseno_mezcla": "H-210-45-19-G",
  "volumen": 5.0
}
```

#### Campos del Request
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `diseno_mezcla` | string | Sí | Código del diseño de mezcla |
| `volumen` | number | Sí | Volumen en m³ (debe ser > 0) |

#### Response Success (200 OK)
```json
{
  "consumos": [
    {
      "material": "Cemento",
      "dosificacion": 350.0,
      "consumo_total": 1750.0,
      "unidad": "kg",
      "stock_actual": 50000.0,
      "stock_minimo": 10000.0,
      "saldo": 48250.0,
      "alerta": false
    },
    {
      "material": "Arena",
      "dosificacion": 800.0,
      "consumo_total": 4000.0,
      "unidad": "kg",
      "stock_actual": 5000.0,
      "stock_minimo": 8000.0,
      "saldo": 1000.0,
      "alerta": true
    }
  ],
  "stock_suficiente": false,
  "alertas": [
    {
      "material": "Arena",
      "stock_actual": 5000.0,
      "stock_minimo": 8000.0,
      "saldo": 1000.0,
      "consumo_total": 4000.0
    }
  ],
  "mensaje": "Stock insuficiente en 1 material(es)"
}
```

#### Response Error (400 Bad Request)
```json
{
  "error": "Falta el diseño de mezcla"
}
```

#### Códigos de Estado
- `200 OK`: Consumos calculados exitosamente
- `400 Bad Request`: Faltan parámetros o valores inválidos
- `500 Internal Server Error`: Error inesperado

---

## API Registro

### `POST /api/registro`

Registra un nuevo despacho de concreto y actualiza el inventario de materiales.

#### Request Body
```json
{
  "fecha": "2026-01-12",
  "volumen": 5.0,
  "diseno_mezcla": "H-210-45-19-G",
  "wbs": "WBS-001",
  "destino": "Zona Norte",
  "turno": "Diurno",
  "humedad_arena": 3.5,
  "asentamiento_final": 18.0,
  "temperatura": 25.0,
  "usuario_id": 1
}
```

#### Campos del Request
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `fecha` | string | Sí | Fecha del despacho (YYYY-MM-DD) |
| `volumen` | number | Sí | Volumen en m³ |
| `diseno_mezcla` | string | Sí | Código del diseño de mezcla |
| `wbs` | string | Sí | Código WBS |
| `destino` | string | Sí | Zona de destino |
| `turno` | string | Sí | Turno (Diurno/Nocturno) |
| `humedad_arena` | number | Sí | Humedad de arena en % (0-100) |
| `asentamiento_final` | number | Sí | Asentamiento final en cm (≥0) |
| `temperatura` | number | Sí | Temperatura en °C (-10 a 60) |
| `usuario_id` | number | No | ID del usuario (default: 1) |

#### Response Success (201 Created)
```json
{
  "mensaje": "Despacho registrado exitosamente",
  "despacho_id": 123
}
```

#### Response Error - Stock Insuficiente (400 Bad Request)
```json
{
  "error": "Stock insuficiente para realizar el despacho",
  "mensaje": "Stock insuficiente en 2 material(es)",
  "consumos": [...],
  "alertas": [
    {
      "material": "Arena",
      "stock_actual": 5000.0,
      "stock_minimo": 8000.0,
      "saldo": 1000.0,
      "consumo_total": 4000.0
    }
  ],
  "stock_suficiente": false
}
```

#### Response Error - Campos Faltantes (400 Bad Request)
```json
{
  "error": "Campos requeridos faltantes: fecha, volumen"
}
```

#### Response Error - Sin JSON (400 Bad Request)
```json
{
  "error": "No se recibieron datos JSON"
}
```

#### Response Error - Inserción Fallida (500 Internal Server Error)
```json
{
  "error": "Error al insertar el despacho en la base de datos"
}
```

#### Códigos de Estado
- `201 Created`: Despacho registrado exitosamente
- `400 Bad Request`: Datos inválidos o stock insuficiente
- `500 Internal Server Error`: Error en el servidor

---

## API Estado de Materiales

### `GET /api/materiales/estado`

Obtiene el estado completo de todos los materiales en el inventario.

#### Request
No requiere parámetros.

#### Response Success (200 OK)
```json
[
  {
    "material": "Cemento",
    "unidad": "kg",
    "stock_actual": 50000.0,
    "stock_minimo": 10000.0,
    "estado": "ok"
  },
  {
    "material": "Arena",
    "unidad": "kg",
    "stock_actual": 4500.0,
    "stock_minimo": 5000.0,
    "estado": "bajo"
  },
  {
    "material": "Grava",
    "unidad": "kg",
    "stock_actual": 80000.0,
    "stock_minimo": 15000.0,
    "estado": "ok"
  }
]
```

#### Estados Posibles
- `"ok"`: Stock actual > Stock mínimo
- `"bajo"`: Stock actual ≤ Stock mínimo

#### Response Error (500 Internal Server Error)
```json
{
  "error": "No se pudieron obtener los materiales"
}
```

#### Códigos de Estado
- `200 OK`: Datos obtenidos exitosamente
- `500 Internal Server Error`: Error al obtener los datos

---

## API Agregar Material

### `POST /api/materiales/agregar`

Agrega stock a un material existente en el inventario.

#### Request Body
```json
{
  "material": "Cemento",
  "stock": 5000.0,
  "unidad": "kg",
  "usuario_id": 1
}
```

#### Campos del Request
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `material` | string | Sí | Nombre del material |
| `stock` | number | Sí | Cantidad a agregar (≥0) |
| `unidad` | string | Sí | Unidad de medida (kg, lt, m3, etc.) |
| `usuario_id` | number | No | ID del usuario (default: 1) |

#### Response Success (201 Created)
```json
{
  "mensaje": "Stock agregado exitosamente a Cemento",
  "material_id": 1
}
```

#### Response Error - Sin JSON (400 Bad Request)
```json
{
  "error": "No se recibieron datos JSON"
}
```

#### Response Error - Campo Faltante (400 Bad Request)
```json
{
  "error": "El campo 'material' es requerido"
}
```

#### Response Error - Stock Negativo (400 Bad Request)
```json
{
  "error": "El stock debe ser un valor positivo"
}
```

#### Response Error - Stock Inválido (400 Bad Request)
```json
{
  "error": "El stock debe ser un valor numérico válido"
}
```

#### Response Error - Material No Existe (500 Internal Server Error)
```json
{
  "error": "No se pudo agregar el stock. Verifique que el material exista."
}
```

#### Códigos de Estado
- `201 Created`: Stock agregado exitosamente
- `400 Bad Request`: Datos inválidos o faltantes
- `500 Internal Server Error`: Error al agregar el stock

---

## Códigos de Estado HTTP Utilizados

| Código | Descripción | Uso en la API |
|--------|-------------|---------------|
| `200 OK` | Solicitud exitosa | GET exitosos, cálculos completados |
| `201 Created` | Recurso creado exitosamente | POST de registro, agregar stock |
| `400 Bad Request` | Solicitud inválida | Parámetros faltantes, valores inválidos, validaciones fallidas |
| `404 Not Found` | Recurso no encontrado | (No implementado aún) |
| `500 Internal Server Error` | Error del servidor | Errores de base de datos, excepciones no controladas |

---

## Notas Generales

### Headers Requeridos
Todas las peticiones POST deben incluir:
```
Content-Type: application/json
```

### Formato de Fechas
Todas las fechas deben estar en formato ISO 8601: `YYYY-MM-DD`

### Codificación
Todas las respuestas son enviadas con `charset=utf-8` y `ensure_ascii=False` para soportar caracteres especiales.

### Manejo de Errores
Todos los endpoints capturan excepciones y retornan:
```json
{
  "error": "Descripción del error"
}
```

### CORS
El servidor actualmente no tiene configuración CORS. Para uso en producción, considere agregar:
```python
from flask_cors import CORS
CORS(app)
```

---

## Ejemplos de Uso con cURL

### Dashboard
```bash
curl -X GET http://localhost:5000/api/dashboard
```

### Historial
```bash
curl -X GET "http://localhost:5000/api/historial?inicio=2025-01-01&fin=2025-12-31"
```

### Calcular Consumos
```bash
curl -X POST http://localhost:5000/api/consumos \
  -H "Content-Type: application/json" \
  -d '{"diseno_mezcla": "H-210-45-19-G", "volumen": 5.0}'
```

### Registrar Despacho
```bash
curl -X POST http://localhost:5000/api/registro \
  -H "Content-Type: application/json" \
  -d '{
    "fecha": "2026-01-12",
    "volumen": 5.0,
    "diseno_mezcla": "H-210-45-19-G",
    "wbs": "WBS-001",
    "destino": "Zona Norte",
    "turno": "Diurno",
    "humedad_arena": 3.5,
    "asentamiento_final": 18.0,
    "temperatura": 25.0,
    "usuario_id": 1
  }'
```

### Estado de Materiales
```bash
curl -X GET http://localhost:5000/api/materiales/estado
```

### Agregar Stock
```bash
curl -X POST http://localhost:5000/api/materiales/agregar \
  -H "Content-Type: application/json" \
  -d '{
    "material": "Cemento",
    "stock": 5000.0,
    "unidad": "kg",
    "usuario_id": 1
  }'
```

---

## Ejemplos de Uso con Python (requests)

```python
import requests
import json

base_url = "http://localhost:5000"

# Dashboard
response = requests.get(f"{base_url}/api/dashboard")
print(response.json())

# Historial con filtros
params = {
    "inicio": "2025-01-01",
    "fin": "2025-12-31",
    "diseno": "H-210-45-19-G"
}
response = requests.get(f"{base_url}/api/historial", params=params)
print(response.json())

# Calcular consumos
data = {
    "diseno_mezcla": "H-210-45-19-G",
    "volumen": 5.0
}
response = requests.post(f"{base_url}/api/consumos", json=data)
print(response.json())

# Registrar despacho
despacho = {
    "fecha": "2026-01-12",
    "volumen": 5.0,
    "diseno_mezcla": "H-210-45-19-G",
    "wbs": "WBS-001",
    "destino": "Zona Norte",
    "turno": "Diurno",
    "humedad_arena": 3.5,
    "asentamiento_final": 18.0,
    "temperatura": 25.0,
    "usuario_id": 1
}
response = requests.post(f"{base_url}/api/registro", json=despacho)
print(response.json())

# Estado de materiales
response = requests.get(f"{base_url}/api/materiales/estado")
print(response.json())

# Agregar stock
material = {
    "material": "Cemento",
    "stock": 5000.0,
    "unidad": "kg",
    "usuario_id": 1
}
response = requests.post(f"{base_url}/api/materiales/agregar", json=material)
print(response.json())
```
