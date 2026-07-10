# Sistema de Gestión de Consumo de Materiales — Minería

Sistema web desarrollado con **Flask** y **SQLite** para gestionar el consumo diario de
materiales en una planta de producción de concreto (despachos / lotes). Cubre el ciclo
completo: catálogos (diseños de mezcla, zonas, centros de costo, turnos), inventario de
insumos con auditoría de movimientos, registro de despachos con cálculo automático de
consumo, historial filtrable y cruce de consumo vs stock disponible. Incluye autenticación
con hashing, control de acceso por roles (Admin / Operador / Visualizador), protección
CSRF, rate limiting, headers de seguridad y bloqueo persistente contra fuerza bruta.

---

## Tabla de contenidos

- [Características principales](#características-principales)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Modelo de datos (3FN)](#modelo-de-datos-3fn)
- [Instalación y configuración inicial](#instalación-y-configuración-inicial)
- [Uso del sistema](#uso-del-sistema)
- [Autenticación y roles](#autenticación-y-roles)
- [Seguridad implementada](#seguridad-implementada)
- [Documentación adicional](#documentación-adicional)
- [Solución de problemas](#solución-de-problemas)

---

## Características principales

### Gestión operativa

- **Dashboard**: KPIs de producción diaria (m³ producidos hoy), registros de los últimos
  7 días e inventario en alerta (OK / Cerca / Bajo mínimo).
- **Registro de despachos**: formulario guiado que valida fecha, volumen, turno, zona,
  WBS, humedad de arena (4–10 %), asentamiento (15–30 cm) y temperatura (−10 a 50 °C).
  Antes de guardar, ejecuta un **cruce consumo vs stock** que bloquea el guardado si el
  despacho dejaría algún insumo en déficit.
- **Inventario de insumos**: alta de materiales con unidad (kg / l / m3 / unidad),
  stock actual, mínimo y máximo; edición de stock y de márgenes; todo movimiento
  (INGRESO / EGRESO / AJUSTE) queda registrado en la tabla `movimientos`.
- **Historial filtrable** por rango de fechas, diseño de mezcla, zona, turno y WBS.
  Devuelve filas pivoteadas (una columna por insumo) más un resumen agregado y un
  cruce de consumo vs stock disponible.
- **Cruce consumo vs stock**: valida un despacho individual (pre-guardado) o un rango
  completo de despachos contra el inventario actual, marcando cada insumo como
  `OK`, `Bajo mínimo` o `Déficit`.

### Seguridad y control de acceso

- **Autenticación contra la base de datos** con contraseñas hasheadas (Werkzeug
  `pbkdf2:sha256`).
- **Control de acceso por roles**: Admin, Operador y Visualizador con decorators
  `@solo_admin`, `@admin_u_operador`, `@cualquier_usuario`.
- **Protección CSRF** global con Flask-WTF.
- **Rate limiting** en `/api/login` (5 intentos por minuto) y **bloqueo persistente de
  24 horas** tras 5 intentos fallidos (sobrevive reinicios del servidor).
- **Timeout de inactividad** de 15 minutos.
- **Headers de seguridad** en todas las respuestas y `Cache-Control: no-store` en rutas
  protegidas.
- **Logging de auditoría** en `seguridad.log` para logins, bloqueos, denegaciones de
  rol, creación de despachos y ajustes de inventario.

> Para el detalle completo ver [`docs/seguridad_implementada.md`](docs/seguridad_implementada.md).

---

## Stack tecnológico

| Capa            | Tecnología                                   |
|-----------------|----------------------------------------------|
| Backend         | Flask ≥ 2.3                                  |
| Base de datos   | SQLite 3 (esquema relacional en 3FN)         |
| Autenticación   | Werkzeug (`generate_password_hash`)          |
| Protección CSRF | Flask-WTF (`CSRFProtect`)                    |
| Rate limiting   | flask-limiter (almacenamiento en memoria)    |
| Configuración   | python-dotenv (`SECRET_KEY`, `DB_PATH`)      |
| Carga de Excel  | openpyxl ≥ 3.1                               |
| Frontend        | HTML + CSS + JavaScript vanilla (sin build)  |

> `requirements.txt` también lista `flask-cors` y `joblib`, que en la versión actual
> del código no se usan; se conservan por compatibilidad con extensiones futuras.

---

## Estructura del proyecto

```
consumo-materiales-mineria/
├── app.py                         # Aplicación Flask (rutas HTML + API + middlewares)
├── requirements.txt               # Dependencias Python
├── README.md                      # Este archivo
│
├── auth/                          # Autenticación y control de acceso
│   ├── __init__.py
│   ├── login.py                   # Hashing, verificación, bloqueo por intentos
│   ├── roles.py                   # Decoradores: solo_admin, admin_u_operador, cualquier_usuario
│   └── usuarios.py                # CRUD de usuarios (validaciones, alta, listado)
│
├── db/                            # Esquema y datos
│   ├── __init__.py
│   ├── gestion_materiales.db      # Base de datos SQLite (se genera al ejecutar el esquema)
│   ├── 01_crear_esquema.py        # Crea las 11 tablas del esquema 3FN
│   ├── 02_poblar_insumos.py       # Puebla Insumos (12 materiales) + 3 usuarios demo
│   ├── 03_cargar_datos_iniciales.py  # Migra el histórico desde el Excel
│   ├── utilidades.py              # Helpers (limpiar_numero para Excel)
│   ├── ver_datos.py               # Debug: imprime 5 filas de cada tabla
│   ├── ver_recetas.py             # Debug: pivotea Receta_Detalle
│   └── verificador_tablas.py      # Verifica que las tablas existan
│
├── services/                      # Lógica de negocio
│   ├── __init__.py
│   ├── dashboard.py               # KPIs (consumo_diario, registros_ultima_semana)
│   ├── despachos.py               # Inserta despacho + descuenta stock + audita
│   ├── historial.py               # Historial filtrable + resumen agregado
│   └── inventario.py              # CRUD de materiales + cruce consumo vs stock
│
├── utils/                         # Utilidades transversales
│   ├── __init__.py
│   ├── db.py                      # conectar(), RUTA_BD, whitelist de tablas
│   └── logging_seguridad.py       # logger_seguridad → seguridad.log + stdout
│
├── scripts/                       # Scripts de mantenimiento
│   ├── __init__.py
│   ├── crear_usuarios.py          # Crea / resetea usuarios demo (variantes con !)
│   └── crear_tabla_intentos.py    # Crea intentos_login si falta (legacy)
│
├── templates/                     # Plantillas Jinja2
│   ├── login.html
│   ├── dashboard.html
│   ├── registro.html
│   ├── inventario.html
│   ├── historial.html
│   └── usuarios.html
│
├── static/js/                     # JavaScript del frontend
│   ├── dashboard.js
│   ├── registro.js
│   ├── historial.js
│   └── usuarios.js
│
├── data/
│   ├── raw/
│   │   ├── Batch_Plant_Production_2025.xlsm   # Histórico de despachos (entrada)
│   │   └── Datos_Stat_Model.csv               # Datos estadísticos (referencia)
│   └── processed/                             # Salidas de procesos (vacío por defecto)
│
└── docs/                          # Documentación
    ├── API_DOCUMENTATION.md
    ├── seguridad_implementada.md
    ├── diagrama_relacional_original.mermaid   # Estado 1FN (histórico)
    ├── diagrama_relacional_2FN.mermaid        # Estado 2FN (intermedio)
    └── diagrama_relacional_3FN.mermaid        # Esquema final implementado
```

---

## Modelo de datos (3FN)

El esquema relacional está en **Tercera Forma Normal** y contiene **11 tablas**. La
fuente de verdad es `db/01_crear_esquema.py`. El diagrama visual está en
[`docs/diagrama_relacional_3FN.mermaid`](docs/diagrama_relacional_3FN.mermaid).

### Tablas del catálogo

| Tabla            | PK              | Columnas principales                              |
|------------------|-----------------|---------------------------------------------------|
| `Zonas`          | `id_zona`       | `nombre_zona` (UNIQUE)                            |
| `Centros_Costo`  | `id_cc`         | `codigo_cc` (UNIQUE)                              |
| `Turnos`         | `id_turno`      | `nombre_turno` (UNIQUE) — Diurno / Nocturno       |
| `Disenos_Mezcla` | `diseno_mezcla` | — catálogo monobranquial de diseños               |

### Tablas de inventario y recetas

| Tabla             | PK                                | Columnas principales                            |
|-------------------|-----------------------------------|------------------------------------------------|
| `Insumos`         | `id_insumo`                       | `nombre_insumo` (UNIQUE), `unidad`, `stock_minimo`, `stock_maximo`, `stock_actual` |
| `Receta_Detalle`  | `id_receta` + UNIQUE(`diseno_mezcla`,`id_insumo`) | `cantidad_requerida` — FK a `Disenos_Mezcla` (CASCADE) y `Insumos` |
| `movimientos`     | `id`                              | `usuario_id` → `usuarios`, `id_insumo` → `Insumos`, `cantidad`, `fecha`, `tipo` (INGRESO/EGRESO/AJUSTE) |

### Tablas de producción

| Tabla                 | PK                                        | Columnas principales                                                              |
|-----------------------|-------------------------------------------|-----------------------------------------------------------------------------------|
| `Produccion_Diaria`   | `id_produccion`                           | `fecha`, `lote_numero`, `volumen_m3`, `diseno_mezcla` (FK), `id_zona` (FK), `id_cc` (FK), `arena_humedad_pct`, `asentamiento_final_cm`, `temperatura_c`, `id_turno` (FK) |
| `Produccion_Insumos`  | (`id_produccion`, `id_insumo`) compuesta  | `cantidad_real` — FK a `Produccion_Diaria` (CASCADE) y `Insumos`                  |

### Tablas de seguridad

| Tabla            | PK      | Columnas principales                                                   |
|------------------|---------|------------------------------------------------------------------------|
| `usuarios`       | `id`    | `username` (UNIQUE), `rol` (Admin/Operador/Visualizador), `password_hash` |
| `intentos_login` | `clave` | `clave = "{username}@{ip}"`, `intentos`, `bloqueado_hasta` (timestamp unix) |

### Relaciones principales

- `usuarios` 1 ─ N `movimientos` (quién hizo el cambio de stock)
- `Insumos` 1 ─ N `movimientos` (qué insumo se movió)
- `Insumos` 1 ─ N `Receta_Detalle` (qué insumos forman cada diseño)
- `Disenos_Mezcla` 1 ─ N `Receta_Detalle`
- `Disenos_Mezcla` 1 ─ N `Produccion_Diaria`
- `Zonas` / `Centros_Costo` / `Turnos` 1 ─ N `Produccion_Diaria`
- `Produccion_Diaria` 1 ─ N `Produccion_Insumos` (consumos reales del despacho)
- `Insumos` 1 ─ N `Produccion_Insumos`

---

## Instalación y configuración inicial

### Requisitos previos

- Python 3.10 o superior
- Acceso al archivo `data/raw/Batch_Plant_Production_2025.xlsm` (incluido en el
  repositorio) para la migración histórica

### 1. Crear y activar un entorno virtual

```bash
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto (no se versiona):

```env
SECRET_KEY=cambia-esto-por-una-clave-larga-y-aleatoria
DB_PATH=db/gestion_materiales.db
```

> Si `SECRET_KEY` no está definida, `app.py` lanza un `RuntimeError` al arrancar.

### 4. Crear la base de datos y cargar datos

Ejecuta los scripts en orden. El paso 3 solo es necesario si quieres migrar el
histórico desde el Excel:

```bash
# Paso 1 — Crear esquema (11 tablas en 3FN)
python db/01_crear_esquema.py

# Paso 2 — Poblar insumos base + usuarios demo
python db/02_poblar_insumos.py

# Paso 3 (opcional) — Migrar despachos históricos desde el Excel
python db/03_cargar_datos_iniciales.py
```

> ⚠️ `db/01_crear_esquema.py` tiene el flag `PERMITIR_RECREAR_DB = True`, que **borra**
> la base de datos existente antes de recrear. Cámbialo a `False` si quieres preservar
> datos entre ejecuciones.

### 5. (Alternativa) Resetear usuarios demo

Si necesitas recrear los usuarios demo con contraseñas que cumplen la política de
complejidad (letra + número + símbolo), ejecuta:

```bash
python scripts/crear_usuarios.py
```

Esto reemplaza los usuarios creados por `02_poblar_insumos.py` por las siguientes
credenciales:

| Usuario   | Contraseña   | Rol           |
|-----------|--------------|---------------|
| `admin`   | `Admin123!`  | Admin         |
| `operador`| `Operador123!` | Operador    |
| `visor`   | `Visor123!`  | Visualizador  |

> ⚠️ Cambia estas contraseñas antes de cualquier despliegue real.

---

## Uso del sistema

### Iniciar el servidor

```bash
python app.py
```

La aplicación queda disponible en `http://localhost:5000`.

### Páginas web

| Ruta          | Rol mínimo        | Descripción                                              |
|---------------|-------------------|----------------------------------------------------------|
| `/login`      | (público)         | Formulario de inicio de sesión                           |
| `/dashboard`  | Cualquier usuario | KPIs, registros recientes, alertas de inventario         |
| `/registro`   | Admin / Operador  | Alta de despachos con cruce consumo vs stock              |
| `/inventario` | Admin             | Gestión de materiales (alta, edición de stock y márgenes) |
| `/historial`  | Admin / Operador  | Búsqueda filtrable de despachos + resumen + alertas       |
| `/usuarios`   | Admin             | Alta y listado de usuarios del sistema                   |
| `/logout`     | —                 | Cierra sesión y vuelve al login                           |

### API REST

El sistema expone **17 rutas** (HTML + JSON). Para el listado completo con métodos,
parámetros, ejemplos de request/response y códigos HTTP, consulta
[`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md).

Resumen rápido:

| Endpoint                        | Método        | Rol                |
|---------------------------------|---------------|--------------------|
| `/api/login`                    | POST          | (público)          |
| `/api/csrf-token`               | GET           | Cualquier usuario  |
| `/api/dashboard`                | GET           | Cualquier usuario  |
| `/api/recetas`                  | GET           | Cualquier usuario  |
| `/api/zonas`                    | GET           | Cualquier usuario  |
| `/api/despachos`                | GET, POST     | Admin / Operador   |
| `/api/historial_consumo`        | GET           | Admin / Operador   |
| `/api/resumen_consumo`          | GET           | Admin / Operador   |
| `/api/alertas_consumo`          | GET           | Cualquier usuario  |
| `/api/cruce_consumo_registro`   | POST          | Admin / Operador   |
| `/api/materiales`               | GET, POST     | Admin              |
| `/api/usuarios`                 | GET, POST     | Admin              |
| `/logout`                       | GET           | (público)          |

> Todas las rutas `/api/*` (excepto `/api/login`) requieren sesión activa y rol
> apropiado. Los POST deben incluir el header `X-CSRFToken`.

---

## Autenticación y roles

### Roles disponibles

| Rol            | Descripción                                                                                       |
|----------------|---------------------------------------------------------------------------------------------------|
| `Admin`        | Acceso total: ver, crear, editar y eliminar cualquier dato, incluidos usuarios e inventario.      |
| `Operador`     | Registrar y consultar despachos, ver dashboard e historial. No gestiona usuarios ni inventario.   |
| `Visualizador` | Solo dashboard y consultas de solo lectura (KPIs, alertas, recetas, zonas).                       |

### Decoradores disponibles (`auth/roles.py`)

- `@solo_admin` — solo `Admin`.
- `@admin_u_operador` — `Admin` o `Operador`.
- `@cualquier_usuario` — cualquier usuario autenticado.
- `@rol_requerido(*roles)` — para roles personalizados.

Cada denegación se registra en `seguridad.log` con el usuario, la IP y la ruta
solicitada.

### Política de contraseñas

- Longitud máxima: **128 caracteres** (para evitar abuso de hashing).
- Debe contener al menos **una letra, un número y un símbolo**.
- El username no puede exceder **50 caracteres** y debe ser único (case-insensitive).
- Las contraseñas se almacenan con `pbkdf2:sha256` (Werkzeug) — nunca en texto plano.

### Bloqueo anti-fuerza-bruta

- Después de **5 intentos fallidos** para el mismo `username@ip`, la cuenta queda
  bloqueada **24 horas** (`BLOQUEO_SEGUNDOS = 24 * 60 * 60` en `auth/login.py`).
- El bloqueo se persiste en la tabla `intentos_login`, así que **sobrevive reinicios**
  del servidor.
- En paralelo, `/api/login` está limitado por `flask-limiter` a **5 peticiones por
  minuto** por IP.

### Timeout de inactividad

- Tras **15 minutos** sin actividad (`INACTIVIDAD_MAX_SEGUNDOS = 15 * 60` en `app.py`),
  la sesión se cierra automáticamente en el siguiente request.

---

## Seguridad implementada

Resumen de las **18 medidas** activas en el proyecto (detalle completo en
[`docs/seguridad_implementada.md`](docs/seguridad_implementada.md)):

1. Hashing de contraseñas con Werkzeug (`pbkdf2:sha256`).
2. Longitud máxima de contraseña (128 caracteres).
3. Política de complejidad (letra + número + símbolo).
4. `SECRET_KEY` desde variables de entorno (sin hardcoded).
5. Cookie de sesión endurecida (`HttpOnly`, `SameSite=Lax`, nombre `ph_session`).
6. Timeout de inactividad de 15 minutos.
7. Rate limiting en `/api/login` (5/min).
8. Bloqueo persistente de 24 horas tras 5 intentos fallidos.
9. Control de acceso por roles (Admin / Operador / Visualizador).
10. Protección CSRF global con Flask-WTF.
11. Headers de seguridad (`X-Frame-Options`, `X-Content-Type-Options`,
    `X-XSS-Protection`, `Referrer-Policy`) + `Cache-Control: no-store` en rutas
    protegidas.
12. Prevención de SQL injection: consultas parametrizadas y whitelist de tablas en
    `PRAGMA table_info`.
13. Validación de entradas (fecha ISO, números no negativos, rangos, unidades, usernames
    únicos case-insensitive).
14. Logging de seguridad dedicado (`seguridad.log`).
15. Mensajes de error genéricos al cliente; trazas solo en logs.
16. Ruta de base de datos configurable por entorno (`DB_PATH`).
17. No exposición de datos sensibles: `listar_usuarios` nunca devuelve `password_hash`.
18. Pista de auditoría: todo cambio de stock queda en `movimientos` con `usuario_id`,
    `cantidad`, `fecha` y `tipo`.

---

## Documentación adicional

- [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md) — Referencia completa de la
  API REST con ejemplos en cURL y JSON.
- [`docs/seguridad_implementada.md`](docs/seguridad_implementada.md) — Detalle de las
  18 medidas de seguridad implementadas.
- [`docs/diagrama_relacional_original.mermaid`](docs/diagrama_relacional_original.mermaid)
  — Diseño inicial desnormalizado (1FN, histórico).
- [`docs/diagrama_relacional_2FN.mermaid`](docs/diagrama_relacional_2FN.mermaid)
  — Estado intermedio 2FN (catálogos separados, receta aún plana).
- [`docs/diagrama_relacional_3FN.mermaid`](docs/diagrama_relacional_3FN.mermaid)
  — Esquema final implementado con las 11 tablas.

---

## Solución de problemas

### `RuntimeError: SECRET_KEY no definida`

Falta la variable de entorno. Crea un archivo `.env` en la raíz con
`SECRET_KEY=<valor>` y reinicia el servidor.

### `sqlite3.OperationalError: no such table: ...`

No se ejecutó el esquema. Corre:

```bash
python db/01_crear_esquema.py
python db/02_poblar_insumos.py
```

### El bloqueo de login no se libera tras 24 horas

El campo `bloqueado_hasta` es un timestamp unix. Para forzar el desbloqueo, ejecuta
directamente contra la base de datos:

```bash
sqlite3 db/gestion_materiales.db "DELETE FROM intentos_login WHERE clave='usuario@1.2.3.4';"
```

### El frontend muestra "Token CSRF inválido"

El token caduca con la sesión. Recarga la página o llama `GET /api/csrf-token` para
obtener uno nuevo antes del próximo POST.

### Quiero recrear la base de datos desde cero

```bash
rm db/gestion_materiales.db
python db/01_crear_esquema.py
python db/02_poblar_insumos.py
python db/03_cargar_datos_iniciales.py   # opcional, si quieres el histórico
```

---

## Licencia

Proyecto académico para el curso de Estructuras de Datos y Bases de Datos. Uso interno.
