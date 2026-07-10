# Documentación de la API — Consumo de Materiales (Minería)

Esta documentación describe **las 17 rutas HTTP** que expone la aplicación Flask en
`app.py`: 7 rutas HTML y 10 endpoints JSON bajo `/api/*`. Todas las rutas (excepto
`/login`, `/api/login` y `/logout`) requieren sesión autenticada y, según el caso, un
rol específico. Las peticiones `POST` deben incluir el header `X-CSRFToken`.

- **Base URL**: `http://localhost:5000`
- **Content-Type** (POST): `application/json`
- **Codificación**: UTF-8
- **Sesión**: cookie `ph_session` (`HttpOnly`, `SameSite=Lax`)

---

## Tabla de contenidos

- [Convenciones](#convenciones)
- [Autenticación y autorización](#autenticación-y-autorización)
- [Rutas HTML](#rutas-html)
- [Rutas API](#rutas-api)
  - [POST /api/login](#post-apilogin)
  - [GET /api/csrf-token](#get-apicsrf-token)
  - [GET /api/dashboard](#get-apidashboard)
  - [GET /api/recetas](#get-apirecetas)
  - [GET /api/zonas](#get-apizonas)
  - [GET /api/despachos](#get-apidespachos)
  - [POST /api/despachos](#post-apidespachos)
  - [GET /api/historial_consumo](#get-apihistorial_consumo)
  - [GET /api/resumen_consumo](#get-apiresumen_consumo)
  - [GET /api/alertas_consumo](#get-apialertas_consumo)
  - [POST /api/cruce_consumo_registro](#post-apicruce_consumo_registro)
  - [GET /api/materiales](#get-apimateriales)
  - [POST /api/materiales](#post-apimateriales)
  - [GET /api/usuarios](#get-apiusuarios)
  - [POST /api/usuarios](#post-apiusuarios)
  - [GET /logout](#get-logout)
- [Manejo de errores](#manejo-de-errores)
- [Ejemplos end-to-end](#ejemplos-end-to-end)

---

## Convenciones

### Estructura de las respuestas JSON

Todas las respuestas exitosas incluyen `"ok": true` y los datos bajo una clave
descriptiva. Las respuestas de error incluyen `"ok": false` y un campo `"error"` con un
mensaje en español apto para mostrar al usuario.

```json
{ "ok": true, "datos": [...] }
```

```json
{ "ok": false, "error": "Mensaje de error legible" }
```

### Códigos HTTP utilizados

| Código | Significado                                                            |
|--------|------------------------------------------------------------------------|
| 200    | OK (GET exitoso o POST exitoso sin creación)                           |
| 201    | Created (POST exitoso que crea un recurso: usuario, material, despacho)|
| 400    | Bad Request (validación fallida)                                       |
| 401    | Unauthorized (no autenticado en rutas API protegidas)                  |
| 403    | Forbidden (rol insuficiente)                                           |
| 404    | Not Found (material inexistente en actualización)                      |
| 409    | Conflict (UNIQUE constraint: username o nombre_insumo duplicado)       |
| 423    | Locked (cuenta bloqueada por intentos fallidos)                        |
| 429    | Too Many Requests (rate limit en `/api/login`)                         |
| 500    | Internal Server Error (mensaje genérico, traceback en `seguridad.log`) |

### Cabeceras requeridas

| Header        | Cuándo                                                            |
|---------------|-------------------------------------------------------------------|
| `Cookie: ph_session=...` | En todas las rutas autenticadas (lo envía el navegador)|
| `X-CSRFToken: <token>`   | En todos los `POST` (excepto `/api/login` que está exento)        |

Para obtener un token CSRF fresco: `GET /api/csrf-token`.

---

## Autenticación y autorización

### Roles

| Rol            | Permisos                                                              |
|----------------|-----------------------------------------------------------------------|
| `Admin`        | Acceso total: usuarios, inventario, despachos, historial, dashboard.  |
| `Operador`     | Despachos, historial, dashboard. No usuarios ni inventario.           |
| `Visualizador` | Solo dashboard, recetas, zonas, alertas (lectura).                    |

### Decoradores aplicados a cada endpoint

| Decorador              | Roles permitidos              |
|------------------------|-------------------------------|
| `@solo_admin`          | `Admin`                       |
| `@admin_u_operador`    | `Admin`, `Operador`           |
| `@cualquier_usuario`   | `Admin`, `Operador`, `Visualizador` |
| (sin decorador)        | público                       |

Si una ruta API protegida se invoca sin sesión, el decorador devuelve **401** con
`{"ok": false, "error": "No has iniciado sesión"}`. Si el rol es insuficiente,
devuelve **403** con `{"ok": false, "error": "No tienes permisos..."}`.

---

## Rutas HTML

Estas rutas devuelven plantillas Jinja2 renderizadas; no son JSON.

| Ruta          | Método | Decorador          | Plantilla        | Descripción                                     |
|---------------|--------|--------------------|------------------|-------------------------------------------------|
| `/`           | GET    | —                  | (redirect)       | Redirige a `/login`                              |
| `/login`      | GET    | —                  | `login.html`     | Página de inicio de sesión                       |
| `/dashboard`  | GET    | `@cualquier_usuario` | `dashboard.html` | KPIs y alertas                                  |
| `/registro`   | GET    | `@admin_u_operador` | `registro.html`  | Formulario de despachos                          |
| `/inventario` | GET    | `@solo_admin`      | `inventario.html`| Gestión de materiales                            |
| `/historial`  | GET    | `@admin_u_operador` | `historial.html` | Búsqueda filtrable                              |
| `/usuarios`   | GET    | `@solo_admin`      | `usuarios.html`  | Gestión de usuarios (inyecta `csrf_token`)       |

Si el usuario no autenticado accede a una ruta HTML protegida, es redirigido a
`/login`. Si está autenticado pero sin rol suficiente, es redirigido a `/dashboard`.

---

## Rutas API

### POST /api/login

Autentica al usuario contra la tabla `usuarios` (hash Werkzeug `pbkdf2:sha256`) y abre
sesión Flask.

- **Decoradores**: `@csrf.exempt`, `@limiter.limit("5 per minute")`
- **Rate limit**: 5 peticiones por minuto por IP. Excederlo devuelve `429`.
- **Bloqueo anti-fuerza-bruta**: tras 5 intentos fallidos para el mismo
  `username@ip`, la cuenta se bloquea 24 horas (persistente en `intentos_login`).
- **Body**:

```json
{
  "usuario": "admin",
  "password": "Admin123!"
}
```

- **Respuesta 200** (éxito):

```json
{
  "ok": true,
  "usuario": {
    "id": 1,
    "username": "admin",
    "rol": "Admin"
  }
}
```

La respuesta setea la cookie `ph_session` y la sesión queda con `usuario_id`,
`username`, `rol` y `ultima_actividad`.

- **Respuesta 401** (credenciales inválidas):

```json
{ "ok": false, "error": "Usuario o contraseña incorrectos" }
```

- **Respuesta 423** (cuenta bloqueada):

```json
{
  "ok": false,
  "error": "Cuenta bloqueada. Intenta de nuevo en 86382 segundos.",
  "bloqueado": true
}
```

- **Ejemplo cURL**:

```bash
curl -c cookies.txt -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "admin", "password": "Admin123!"}'
```

---

### GET /api/csrf-token

Devuelve un token CSRF fresco para usar en los POST.

- **Decorador**: `@cualquier_usuario`
- **Respuesta 200**:

```json
{ "csrf_token": "IjQ3N2QxN..." }
```

- **Uso típico**: el frontend llama este endpoint antes de cualquier POST y envía el
  token en el header `X-CSRFToken`.

---

### GET /api/dashboard

KPIs para el dashboard: producción diaria (m³), registros de los últimos 7 días e
inventario actual mapeado al formato que espera el frontend.

- **Decorador**: `@cualquier_usuario`
- **Parámetros**: ninguno
- **Respuesta 200**:

```json
{
  "consumo_diario": {
    "fecha": "2025-07-08",
    "total_m3": 142.5,
    "cantidad_despachos": 7
  },
  "registros_ultima_semana": [
    {
      "id_produccion": 123,
      "fecha": "2025-07-08",
      "diseno_mezcla": "UCEM-HE",
      "volumen_m3": 24.0,
      "nombre_zona": "ZONA_NORTE",
      "codigo_cc": "WBS-001"
    }
  ],
  "cantidad_registros_semana": 35,
  "inventario": [
    {
      "material": "Cemento",
      "unidad": "kg",
      "stock": 8500.0,
      "minimo": 2000.0
    }
  ]
}
```

> El campo `inventario` proviene de `obtener_materiales()` re-mapeado a las claves
> `material`, `unidad`, `stock`, `minimo` (alias legado del frontend original).

- **Ejemplo cURL**:

```bash
curl -b cookies.txt http://localhost:5000/api/dashboard
```

---

### GET /api/recetas

Lista los códigos de diseño de mezcla disponibles (catálogo `Disenos_Mezcla`).

- **Decorador**: `@cualquier_usuario`
- **Respuesta 200**:

```json
{
  "ok": true,
  "disenos": ["UCEM-HE", "UCEM-OPC", "SHOTCRETE-1"]
}
```

---

### GET /api/zonas

Lista los nombres de zona disponibles (catálogo `Zonas`).

- **Decorador**: `@cualquier_usuario`
- **Respuesta 200**:

```json
{
  "ok": true,
  "zonas": ["ZONA_NORTE", "ZONA_SUR", "ZONA_PLANTA"]
}
```

---

### GET /api/despachos

Endpoint de verificación (stub). Confirma que la ruta está activa.

- **Decorador**: `@admin_u_operador`
- **Respuesta 200**:

```json
{ "ok": true, "msg": "Endpoint activo. Usa POST para guardar." }
```

---

### POST /api/despachos

Crea un despacho (lote de producción) y descuenta stock de los insumos consumidos.

- **Decorador**: `@admin_u_operador`
- **Header requerido**: `X-CSRFToken`
- **Body** (todos los campos son obligatorios salvo los marcados):

```json
{
  "fecha": "2025-07-08",                   // YYYY-MM-DD (obligatorio)
  "volumen_m3": "24.5",                    // > 0 (obligatorio, admite coma decimal)
  "diseno_mezcla": "UCEM-HE",              // debe existir en Disenos_Mezcla (obligatorio)
  "turno": "Diurno",                       // "Diurno" o "Nocturno" (obligatorio)
  "wbs": "WBS-001",                        // código de centro de costo (obligatorio)
  "zona": "ZONA_NORTE",                    // nombre de zona (obligatorio)
  "arena_humedad_pct": "6.5",              // 4 a 10 (opcional)
  "asentamiento_final_cm": "22",           // 15 a 30 (opcional)
  "temperatura_c": "18"                    // -10 a 50 (opcional)
}
```

**Validaciones**:

- `fecha` debe ser ISO `YYYY-MM-DD` válido.
- `volumen_m3` debe ser > 0 y convertible a float (admite coma decimal).
- `diseno_mezcla`, `turno`, `wbs`, `zona` no vacíos.
- `arena_humedad_pct` entre 4 y 10 (si viene).
- `asentamiento_final_cm` entre 15 y 30 (si viene).
- `temperatura_c` entre -10 y 50 (si viene).

**Efectos secundarios**:

1. Inserta una fila en `Produccion_Diaria` (mapeando "Diurno"→`id_turno=1`,
   "Nocturno"→`id_turno=2`).
2. Obtiene o crea las FKs de `Zonas`, `Centros_Costo` y `Disenos_Mezcla` si no existen
   (upsert idempotente).
3. Lee la receta (`Receta_Detalle`) para el diseño, calcula el consumo estimado por
   insumo multiplicando `cantidad_requerida` × `volumen_m3`.
4. Para cada insumo: inserta una fila en `Produccion_Insumos`, descuenta
   `stock_actual` en `Insumos` y registra un movimiento `EGRESO` en `movimientos`
   con el `usuario_id` de la sesión.
5. Registra en `seguridad.log`: `"Despacho creado | id=X usuario=Y ip=Z"`.

- **Respuesta 201**:

```json
{ "ok": true, "id": 124 }
```

- **Respuesta 400** (validación):

```json
{ "ok": false, "error": "El volumen_m3 debe ser mayor que 0. Fecha inválida..." }
```

- **Respuesta 500** (error inesperado):

```json
{ "ok": false, "error": "Ocurrió un error al procesar la solicitud. Intenta de nuevo más tarde." }
```

- **Ejemplo cURL**:

```bash
# 1. Obtener token CSRF
TOKEN=$(curl -b cookies.txt -s http://localhost:5000/api/csrf-token | python -c "import sys, json; print(json.load(sys.stdin)['csrf_token'])")

# 2. Crear despacho
curl -b cookies.txt -X POST http://localhost:5000/api/despachos \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{
    "fecha": "2025-07-08",
    "volumen_m3": "24.5",
    "diseno_mezcla": "UCEM-HE",
    "turno": "Diurno",
    "wbs": "WBS-001",
    "zona": "ZONA_NORTE",
    "arena_humedad_pct": "6.5",
    "asentamiento_final_cm": "22",
    "temperatura_c": "18"
  }'
```

---

### GET /api/historial_consumo

Lista despachos filtrados por rango de fechas y opcionalmente por diseño, zona, turno y
WBS. Devuelve filas pivoteadas (una columna por insumo) para que el frontend las
renderice como tabla ancha.

- **Decorador**: `@admin_u_operador`
- **Query params** (todos viajan en la URL):

| Param     | Requerido | Descripción                                  |
|-----------|-----------|----------------------------------------------|
| `inicio`  | sí        | Fecha inicial `YYYY-MM-DD`                   |
| `fin`     | sí        | Fecha final `YYYY-MM-DD`                     |
| `diseno`  | no        | Filtra por `diseno_mezcla`                   |
| `zona`    | no        | Filtra por `nombre_zona`                     |
| `turno`   | no        | Filtra por `nombre_turno` (Diurno/Nocturno)  |
| `wbs`     | no        | Filtra por `codigo_cc`                       |

- **Respuesta 200**:

```json
{
  "datos": [
    {
      "id": 124,
      "fecha": "2025-07-08",
      "diseno_mezcla": "UCEM-HE",
      "nombre_zona": "ZONA_NORTE",
      "codigo_cc": "WBS-001",
      "nombre_turno": "Diurno",
      "volumen_m3": 24.5,
      "arena_humedad_pct": 6.5,
      "asentamiento_final_cm": 22.0,
      "temperatura_c": 18.0,
      "cemento_kg": 2448.0,
      "arena_kg": 18000.0,
      "grava_kg": 22000.0,
      "agua_kg": 4500.0,
      "aditivo_rheo_sika115": 12.5,
      "aditivo_basf_sika200": 0.0,
      "aditivo_delvo": 0.0,
      "aditivo_glenium_7950": 8.0,
      "aditivo_glenium_7970": 0.0,
      "aditivo_fibras": 0.0
    }
  ],
  "total": 1
}
```

Las filas se ordenan por `fecha` ASC y luego `id` ASC.

- **Respuesta 400** (sin `inicio` o `fin`):

```json
{ "error": "Debes enviar 'inicio' y 'fin'." }
```

- **Ejemplo cURL**:

```bash
curl -b cookies.txt "http://localhost:5000/api/historial_consumo?inicio=2025-07-01&fin=2025-07-08"
```

---

### GET /api/resumen_consumo

Agregados de consumo en el rango filtrado (suma por insumo + total de m³ + número de
registros). Reutiliza los mismos filtros que `/api/historial_consumo`.

- **Decorador**: `@admin_u_operador`
- **Query params**: igual que `/api/historial_consumo` (`inicio` y `fin` obligatorios).
- **Respuesta 200**:

```json
{
  "ok": true,
  "resumen": {
    "registros": 35,
    "volumen_m3": 842.5,
    "cemento_kg": 84000.0,
    "arena_kg": 612000.0,
    "grava_kg": 748000.0,
    "agua_kg": 153000.0,
    "aditivo_rheo_sika115": 430.0,
    "aditivo_basf_sika200": 0.0,
    "aditivo_delvo": 0.0,
    "aditivo_glenium_7950": 280.0,
    "aditivo_glenium_7970": 0.0,
    "aditivo_fibras": 0.0
  },
  "total_registros": 35
}
```

- **Ejemplo cURL**:

```bash
curl -b cookies.txt "http://localhost:5000/api/resumen_consumo?inicio=2025-07-01&fin=2025-07-08&zona=ZONA_NORTE"
```

---

### GET /api/alertas_consumo

Cruza el consumo filtrado del historial contra el stock actual. Marca cada insumo como
`OK`, `Bajo mínimo` o `Déficit`.

- **Decorador**: `@cualquier_usuario` (lectura)
- **Query params**: igual que `/api/historial_consumo` (`inicio` y `fin` obligatorios).
- **Respuesta 200**:

```json
{
  "ok": true,
  "filas": [
    {
      "campo": "cemento_kg",
      "material": "Cemento",
      "unidad": "kg",
      "stock": 8500.0,
      "consumo": 84000.0,
      "saldo": -75500.0,
      "deficit_sugerido": 75500.0,
      "bajo_minimo": true,
      "estado": "Déficit"
    },
    {
      "campo": "arena_kg",
      "material": "Arena",
      "unidad": "kg",
      "stock": 800000.0,
      "consumo": 612000.0,
      "saldo": 188000.0,
      "deficit_sugerido": 0.0,
      "bajo_minimo": false,
      "estado": "OK"
    }
  ],
  "no_mapeados": [],
  "no_encontrados": [],
  "total_registros": 35
}
```

- `no_mapeados`: campos de consumo que no tienen un nombre de insumo asociado en el
  mapeo interno (defensa contra cambios de esquema).
- `no_encontrados`: insumos cuyo nombre no existe en la tabla `Insumos`.

- **Ejemplo cURL**:

```bash
curl -b cookies.txt "http://localhost:5000/api/alertas_consumo?inicio=2025-07-01&fin=2025-07-08"
```

---

### POST /api/cruce_consumo_registro

Valida un despacho **individual** antes de guardarlo. Calcula el consumo estimado para
el `volumen_m3` indicado según la receta del `diseno_mezcla`, y lo cruza contra el stock
actual. El frontend usa esto para habilitar/deshabilitar el botón "Guardar registro".

- **Decorador**: `@admin_u_operador`
- **Header requerido**: `X-CSRFToken`
- **Body**:

```json
{
  "fecha": "2025-07-08",         // YYYY-MM-DD (obligatorio)
  "diseno_mezcla": "UCEM-HE",    // obligatorio
  "volumen_m3": "24.5"           // > 0 (obligatorio, admite coma decimal)
}
```

- **Respuesta 200**:

```json
{
  "ok": true,
  "datos": [
    {
      "campo": "cemento_kg",
      "material": "Cemento",
      "unidad": "kg",
      "stock": 8500.0,
      "consumo": 2448.0,
      "saldo": 6052.0,
      "deficit_sugerido": 0.0,
      "bajo_minimo": false,
      "estado": "OK"
    }
  ],
  "no_mapeados": [],
  "no_encontrados": []
}
```

- **Respuesta 400** (falta diseño o volumen):

```json
{ "ok": false, "error": "Faltan diseno_mezcla o volumen" }
```

- **Ejemplo cURL**:

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/cruce_consumo_registro \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"fecha": "2025-07-08", "diseno_mezcla": "UCEM-HE", "volumen_m3": "24.5"}'
```

---

### GET /api/materiales

Lista todos los insumos del inventario.

- **Decorador**: `@solo_admin`
- **Respuesta 200**:

```json
{
  "ok": true,
  "materiales": [
    {
      "id_insumo": 1,
      "nombre_insumo": "Arena",
      "unidad": "kg",
      "stock_actual": 800000.0,
      "stock_minimo": 200000.0,
      "stock_maximo": 1500000.0
    }
  ]
}
```

---

### POST /api/materiales

Crea un material nuevo o actualiza uno existente, según llegue o no el campo `id`.

- **Decorador**: `@solo_admin`
- **Header requerido**: `X-CSRFToken`

#### Caso 1: crear material nuevo (sin `id`)

- **Body**:

```json
{
  "nombre": "Microsílice",        // obligatorio, no solo números, UNIQUE
  "unidad": "kg",                 // obligatorio, uno de: kg | l | m3 | unidad
  "stock_actual": "500",          // opcional, >= 0 (admite coma decimal)
  "stock_minimo": "100",          // opcional, >= 0
  "stock_maximo": "2000"          // opcional, >= 0 y >= stock_minimo
}
```

- **Efectos**: inserta en `Insumos`; si `stock_actual > 0`, registra un movimiento
  `INGRESO` en `movimientos` con el `usuario_id` de la sesión.
- **Respuesta 201**:

```json
{ "ok": true, "id": 13, "mensaje": "Material creado" }
```

- **Respuesta 409** (UNIQUE constraint):

```json
{ "ok": false, "error": "Ya existe un material con ese nombre" }
```

#### Caso 2: actualizar material existente (con `id`)

- **Body** (todos los campos de stock son opcionales, solo se actualizan los que llegan):

```json
{
  "id": 1,
  "stock_actual": "780000",       // opcional, >= 0
  "stock_minimo": "150000",       // opcional, >= 0
  "stock_maximo": "1600000"       // opcional, >= 0 y >= stock_minimo
}
```

- **Efectos**: actualiza los campos provistos; si `stock_actual` cambió, registra un
  movimiento `AJUSTE` en `movimientos` con el `usuario_id` de la sesión.
- **Respuesta 200**:

```json
{ "ok": true, "mensaje": "Material actualizado" }
```

- **Respuesta 404** (id inexistente):

```json
{ "ok": false, "error": "Material no encontrado" }
```

- **Ejemplo cURL** (crear):

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/materiales \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"nombre": "Microsílice", "unidad": "kg", "stock_actual": "500", "stock_minimo": "100", "stock_maximo": "2000"}'
```

- **Ejemplo cURL** (actualizar):

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/materiales \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"id": 1, "stock_actual": "780000"}'
```

---

### GET /api/usuarios

Lista los usuarios del sistema. Nunca devuelve `password_hash`.

- **Decorador**: `@solo_admin`
- **Respuesta 200**:

```json
{
  "ok": true,
  "usuarios": [
    { "id": 1, "username": "admin", "rol": "Admin" },
    { "id": 2, "username": "operador", "rol": "Operador" },
    { "id": 3, "username": "visor", "rol": "Visualizador" }
  ]
}
```

---

### POST /api/usuarios

Crea un usuario nuevo. El username debe ser único (case-insensitive) y la contraseña
debe cumplir la política de complejidad.

- **Decorador**: `@solo_admin`
- **Header requerido**: `X-CSRFToken`
- **Body**:

```json
{
  "username": "nuevoOperador",       // 1 a 50 caracteres, único case-insensitive
  "password": "Clave123!",           // 1 a 128 caracteres, con letra + número + símbolo
  "rol": "Operador"                  // "Admin" | "Operador" | "Visualizador"
}
```

- **Efectos**: inserta en `usuarios` con `password_hash` (Werkzeug
  `pbkdf2:sha256`).
- **Respuesta 201**:

```json
{
  "ok": true,
  "usuario": { "id": 4, "username": "nuevoOperador", "rol": "Operador" },
  "mensaje": "Usuario creado correctamente."
}
```

- **Respuesta 400** (validación):

```json
{ "ok": false, "error": "La contraseña debe tener al menos una letra, un número y un símbolo." }
```

```json
{ "ok": false, "error": "El nombre de usuario ya existe." }
```

```json
{ "ok": false, "error": "Rol inválido. Debe ser Admin, Operador o Visualizador." }
```

- **Ejemplo cURL**:

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/usuarios \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"username": "nuevoOperador", "password": "Clave123!", "rol": "Operador"}'
```

---

### GET /logout

Cierra la sesión Flask y redirige a `/login`.

- **Decorador**: ninguno
- **Efectos**: `session.clear()`; registra en `seguridad.log`:
  `"Logout | usuario=X ip=Y"`.
- **Respuesta**: `302 Found` → `Location: /login`.

---

## Manejo de errores

### Mensaje genérico

Para evitar filtrar información sensible en errores 500, las rutas devuelven el
mensaje fijo:

```json
{ "ok": false, "error": "Ocurrió un error al procesar la solicitud. Intenta de nuevo más tarde." }
```

El traceback completo se registra en `seguridad.log` y stdout.

### Errores 401 / 403 desde los decoradores

Si una ruta API protegida se invoca sin sesión:

```json
{ "ok": false, "error": "No has iniciado sesión." }   // 401
```

Si el rol es insuficiente:

```json
{ "ok": false, "error": "No tienes permisos para acceder a este recurso." }   // 403
```

### Errores CSRF

Cualquier POST sin `X-CSRFToken` o con token inválido recibe `400 Bad Request` con un
mensaje del estilo `"El token CSRF ha expirado o es inválido"`. El único POST exento
es `/api/login`.

---

## Ejemplos end-to-end

### Flujo completo: crear un despacho

```bash
# 1. Login
curl -c cookies.txt -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "admin", "password": "Admin123!"}'

# 2. Obtener token CSRF
TOKEN=$(curl -b cookies.txt -s http://localhost:5000/api/csrf-token \
  | python -c "import sys, json; print(json.load(sys.stdin)['csrf_token'])")

# 3. Cruce previo (verifica stock antes de guardar)
curl -b cookies.txt -X POST http://localhost:5000/api/cruce_consumo_registro \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"fecha": "2025-07-08", "diseno_mezcla": "UCEM-HE", "volumen_m3": "24.5"}'

# 4. Guardar despacho
curl -b cookies.txt -X POST http://localhost:5000/api/despachos \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{
    "fecha": "2025-07-08",
    "volumen_m3": "24.5",
    "diseno_mezcla": "UCEM-HE",
    "turno": "Diurno",
    "wbs": "WBS-001",
    "zona": "ZONA_NORTE",
    "arena_humedad_pct": "6.5",
    "asentamiento_final_cm": "22",
    "temperatura_c": "18"
  }'

# 5. Ver historial del día
curl -b cookies.txt "http://localhost:5000/api/historial_consumo?inicio=2025-07-08&fin=2025-07-08"

# 6. Ver alertas de stock
curl -b cookies.txt "http://localhost:5000/api/alertas_consumo?inicio=2025-07-08&fin=2025-07-08"

# 7. Logout
curl -b cookies.txt http://localhost:5000/logout
```

### Flujo completo: gestionar inventario

```bash
# Login + token
curl -c cookies.txt -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "admin", "password": "Admin123!"}'

TOKEN=$(curl -b cookies.txt -s http://localhost:5000/api/csrf-token \
  | python -c "import sys, json; print(json.load(sys.stdin)['csrf_token'])")

# Listar materiales
curl -b cookies.txt http://localhost:5000/api/materiales

# Crear material nuevo
curl -b cookies.txt -X POST http://localhost:5000/api/materiales \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"nombre": "Microsílice", "unidad": "kg", "stock_actual": "500", "stock_minimo": "100", "stock_maximo": "2000"}'

# Actualizar stock de un material existente (id=1)
curl -b cookies.txt -X POST http://localhost:5000/api/materiales \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"id": 1, "stock_actual": "780000"}'
```

### Flujo completo: gestionar usuarios

```bash
# Login + token (como admin)
curl -c cookies.txt -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "admin", "password": "Admin123!"}'

TOKEN=$(curl -b cookies.txt -s http://localhost:5000/api/csrf-token \
  | python -c "import sys, json; print(json.load(sys.stdin)['csrf_token'])")

# Listar usuarios
curl -b cookies.txt http://localhost:5000/api/usuarios

# Crear usuario nuevo
curl -b cookies.txt -X POST http://localhost:5000/api/usuarios \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"username": "jefePlanta", "password": "Jefe2025!", "rol": "Operador"}'
```
