from flask import current_app
import sqlite3
from pathlib import Path
from datetime import date
from utils.helpers import ultimos_7_dias


def obtener_conexion_flask():
    """
    Obtiene una conexión a la base de datos dentro del contexto de Flask.
    """
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # permite dict(row)
    return conn


def obtener_conexion_autonoma():
    """
    Obtiene una conexión a la base de datos fuera del contexto de Flask
    (útil para ED, ML o scripts independientes).
    """
    db_path = Path(__file__).parent.parent / "db" / "gestion_materiales.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # permite dict(row)
    return conn


def _get_conn():
    """
    Devuelve conexión en contexto Flask si existe; si no, conexión autónoma.
    """
    try:
        return obtener_conexion_flask()
    except RuntimeError:
        return obtener_conexion_autonoma()


def obtener_columnas_tabla(tabla: str):
    """
    Retorna lista de nombres de columnas para una tabla dada.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({tabla})")
    rows = cur.fetchall()
    conn.close()
    return [r["name"] for r in rows]


def cargar_datos_tabla(tabla: str):
    """
    Carga todos los registros de una tabla específica como lista de diccionarios.
    """
    tablas_permitidas = {"despachos", "movimientos", "recetas", "materiales", "usuarios", "zonas", "centros_costos"}

    if tabla not in tablas_permitidas:
        raise ValueError(f"Tabla '{tabla}' no permitida. Use: {tablas_permitidas}")

    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {tabla}")
    datos = cursor.fetchall()
    conn.close()

    return [dict(fila) for fila in datos]


def consumo_diario():
    try:
        datos = cargar_datos_tabla("despachos")
        hoy = date.today().isoformat()
        consumo = 0.0

        for entrada in datos:
            if entrada.get("fecha") == hoy:
                volumen = entrada.get("volumen_m3", 0)
                try:
                    consumo += float(volumen)
                except (ValueError, TypeError):
                    pass

        return consumo
    except Exception as e:
        print(f"Error al calcular consumo diario: {e}")
        return 0.0


def registros_ultima_semana():
    """
    Devuelve (lista_registros_filtrados, total_registros)
    Filtra por los últimos 7 días y retorna campos mínimos para dashboard.
    """
    try:
        fechas = set(ultimos_7_dias())
        datos = cargar_datos_tabla("despachos")
        datos_finales = []

        for entrada in datos:
            if entrada.get("fecha") in fechas:
                registro_filtrado = {
                    "fecha": entrada.get("fecha", ""),
                    "diseno_mezcla": entrada.get("diseno_mezcla", ""),
                    "zona": entrada.get("zona", ""),
                    "wbs": entrada.get("wbs", ""),
                    "volumen_m3": entrada.get("volumen_m3", 0),
                    "turno": entrada.get("turno", ""),
                }
                datos_finales.append(registro_filtrado)

        total_registros = len(datos_finales)
        return datos_finales, total_registros

    except Exception as e:
        print(f"Error al obtener registros de la última semana: {e}")
        return [], 0


def insertar_despacho(
    fecha,
    volumen,
    diseno_mezcla,
    wbs,
    destino,            # esto se guarda en columna "zona"
    turno,
    humedad_arena,
    asentamiento_final,
    temperatura,
):
    """
    Inserta un nuevo registro en la tabla 'despachos' usando receta.

    - despachos tiene columna: volumen_m3, zona, turno, etc.
    - recetas se busca por: codigo_diseno
    """
    # ===== Validaciones básicas =====
    if not fecha or not isinstance(fecha, str):
        print("Error: Fecha inválida o vacía")
        return None

    if not diseno_mezcla or not isinstance(diseno_mezcla, str):
        print("Error: Diseño de mezcla inválido o vacío")
        return None

    if not wbs or not isinstance(wbs, str):
        print("Error: WBS inválido o vacío")
        return None

    if not destino or not isinstance(destino, str):
        print("Error: Destino inválido o vacío")
        return None

    if not turno or not isinstance(turno, str):
        print("Error: Turno inválido o vacío")
        return None

    # Validar formato de fecha (YYYY-MM-DD)
    try:
        from datetime import datetime
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Formato de fecha inválido. Use 'YYYY-MM-DD'. Recibido: {fecha}")
        return None

    # Validar valores numéricos
    try:
        volumen = float(volumen)
        humedad_arena = float(humedad_arena)
        asentamiento_final = float(asentamiento_final)
        temperatura = float(temperatura)
    except (ValueError, TypeError):
        print("Error: Uno o más valores numéricos son inválidos")
        return None

    # Validar rangos razonables
    if volumen <= 0:
        print(f"Error: El volumen debe ser positivo. Recibido: {volumen}")
        return None

    if not (0 <= humedad_arena <= 100):
        print(f"Error: La humedad debe estar entre 0 y 100%. Recibido: {humedad_arena}")
        return None

    if asentamiento_final < 0:
        print(f"Error: El asentamiento no puede ser negativo. Recibido: {asentamiento_final}")
        return None

    if not (-10 <= temperatura <= 60):
        print(f"Error: Temperatura fuera de rango razonable (-10 a 60°C). Recibido: {temperatura}")
        return None

    try:
        conn = obtener_conexion_autonoma()
        cursor = conn.cursor()

        # ===== 1) Buscar receta =====
        cursor.execute("SELECT * FROM recetas WHERE codigo_diseno = ?", (diseno_mezcla,))
        receta = cursor.fetchone()

        if not receta:
            print(f"Error: No se encontró la receta para {diseno_mezcla}")
            conn.close()
            return None

        # ===== 2) Mapear receta -> columnas reales en DESPACHOS =====
        cemento_total = receta["cemento_kg"] if "cemento_kg" in receta.keys() and receta["cemento_kg"] is not None else 0.0
        try:
            cemento_total = float(cemento_total)
        except (ValueError, TypeError):
            cemento_total = 0.0

        cemento_he = cemento_total * 0.6
        cemento_ip = cemento_total * 0.4

        campos_despacho = [
            "arena_kg",
            "grava_kg",
            "cemento_he_kg",
            "cemento_ip_kg",
            "agua_kg",
            "aditivo_rheo_sika115",
            "aditivo_basf_sika200",
            "aditivo_delvo",
            "aditivo_glenium_7950",
            "aditivo_glenium_7970",
            "aditivo_fibras",
        ]

        valores_despacho = [
            receta["arena_kg"] if "arena_kg" in receta.keys() and receta["arena_kg"] is not None else 0.0,
            receta["grava_kg"] if "grava_kg" in receta.keys() and receta["grava_kg"] is not None else 0.0,
            cemento_he,
            cemento_ip,
            receta["agua_kg"] if "agua_kg" in receta.keys() and receta["agua_kg"] is not None else 0.0,
            receta["aditivo_a"] if "aditivo_a" in receta.keys() and receta["aditivo_a"] is not None else 0.0,
            receta["aditivo_b"] if "aditivo_b" in receta.keys() and receta["aditivo_b"] is not None else 0.0,
            receta["aditivo_delvo"] if "aditivo_delvo" in receta.keys() and receta["aditivo_delvo"] is not None else 0.0,
            receta["aditivo_glenium_7950"] if "aditivo_glenium_7950" in receta.keys() and receta["aditivo_glenium_7950"] is not None else 0.0,
            receta["aditivo_glenium_7970"] if "aditivo_glenium_7970" in receta.keys() and receta["aditivo_glenium_7970"] is not None else 0.0,
            receta["aditivo_fibras"] if "aditivo_fibras" in receta.keys() and receta["aditivo_fibras"] is not None else 0.0,
        ]

        # ===== 3) Insert en DESPACHOS =====
        query = f"""
        INSERT INTO despachos (
            fecha, diseno_mezcla, lote, zona, wbs, volumen_m3, turno,
            arena_humedad_pct, asentamiento_final_cm, temperatura_c,
            {", ".join(campos_despacho)}
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {", ".join(["?"] * len(campos_despacho))})
        """

        # lote no lo estás usando en UI → lo dejamos NULL
        lote = None

        cursor.execute(
            query,
            (
                fecha,
                diseno_mezcla,
                lote,
                destino,     # guarda en columna "zona"
                wbs,
                volumen,
                turno,
                humedad_arena,
                asentamiento_final,
                temperatura,
                *valores_despacho,
            ),
        )

        despacho_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return despacho_id

    except sqlite3.Error as e:
        print(f"Error al agregar nueva entrada: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return None


# --------------------------
# STOCK / MATERIALES (Paso 3)
# --------------------------

def obtener_materiales():
    """
    Lee materiales sin asumir que existe la columna 'minimo'.
    Retorna lista de dicts con: id, nombre, unidad, minimo (si no existe -> 0)
    """
    cols = set(obtener_columnas_tabla("materiales"))

    # Columna de minimo: intentamos detectar variantes
    candidato_minimos = ["minimo", "minimo_stock", "stock_minimo", "min_stock", "min"]
    col_min = next((c for c in candidato_minimos if c in cols), None)

    base_cols = ["id", "nombre", "unidad"]
    select_cols = base_cols.copy()
    if col_min:
        select_cols.append(col_min)

    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT {', '.join(select_cols)} FROM materiales ORDER BY nombre")
    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        d = dict(r)
        # normalizar a llave "minimo"
        if col_min:
            d["minimo"] = d.get(col_min, 0) if d.get(col_min) is not None else 0
            if col_min != "minimo":
                d.pop(col_min, None)
        else:
            d["minimo"] = 0
        return_cols = {
            "id": d.get("id"),
            "nombre": d.get("nombre", ""),
            "unidad": d.get("unidad", ""),
            "minimo": d.get("minimo", 0),
        }
        out.append(return_cols)

    return out


def obtener_stock_por_material():
    """
    Calcula stock a partir de tabla movimientos:
    - INGRESO suma
    - EGRESO resta
    Retorna dict {material_id: stock}
    """
    # si no existe la tabla movimientos, no reventar
    try:
        cols_mov = set(obtener_columnas_tabla("movimientos"))
    except Exception:
        return {}

    if not cols_mov:
        return {}

    # requerimos mínimo: material_id, cantidad, tipo
    required = {"material_id", "cantidad", "tipo"}
    if not required.issubset(cols_mov):
        return {}

    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT material_id, cantidad, tipo FROM movimientos")
    rows = cur.fetchall()
    conn.close()

    stock = {}
    for r in rows:
        mid = r["material_id"]
        qty = r["cantidad"] if r["cantidad"] is not None else 0
        try:
            qty = float(qty)
        except (ValueError, TypeError):
            qty = 0.0

        t = (r["tipo"] or "").upper().strip()
        if t == "INGRESO":
            stock[mid] = stock.get(mid, 0.0) + qty
        else:
            # cualquier otra cosa lo tratamos como salida
            stock[mid] = stock.get(mid, 0.0) - qty

    # evitar negativos por ruido
    for k in list(stock.keys()):
        if stock[k] < 0:
            stock[k] = 0.0

    return stock


def obtener_stock_catalogo():
    """
    Retorna catálogo:
    { normalizado_nombre_material: {id, nombre, unidad, minimo, stock} }
    """
    mats = obtener_materiales()
    stock_map = obtener_stock_por_material()

    def norm(s: str):
        return str(s or "").strip().lower()

    catalogo = {}
    for m in mats:
        mid = m["id"]
        catalogo[norm(m["nombre"])] = {
            "id": mid,
            "nombre": m["nombre"],
            "unidad": m.get("unidad", ""),
            "minimo": float(m.get("minimo", 0) or 0),
            "stock": float(stock_map.get(mid, 0.0) or 0.0),
        }
    return catalogo


def cruce_consumo_por_rango(inicio: str, fin: str):
    """
    Suma consumos de despachos por material (arena_kg, grava_kg, etc)
    en el rango [inicio, fin].
    Retorna dict {material_normalizado: consumo_total}
    """
    conn = _get_conn()
    cur = conn.cursor()

    # columnas de consumos que existen en despachos según tu tabla
    campos = [
        "arena_kg",
        "grava_kg",
        "cemento_he_kg",
        "cemento_ip_kg",
        "agua_kg",
        "aditivo_rheo_sika115",
        "aditivo_basf_sika200",
        "aditivo_delvo",
        "aditivo_glenium_7950",
        "aditivo_glenium_7970",
        "aditivo_fibras",
    ]

    select_sum = ", ".join([f"SUM({c}) as {c}" for c in campos])
    cur.execute(
        f"""
        SELECT {select_sum}
        FROM despachos
        WHERE fecha >= ? AND fecha <= ?
        """,
        (inicio, fin),
    )
    row = cur.fetchone()
    conn.close()

    def safe_float(x):
        try:
            return float(x) if x is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    # Mapeo a nombres de inventario (ajusta si tus materiales se llaman distinto)
    consumo = {
        "arena": safe_float(row["arena_kg"]),
        "grava": safe_float(row["grava_kg"]),
        "cemento he": safe_float(row["cemento_he_kg"]),
        "cemento ip": safe_float(row["cemento_ip_kg"]),
        "agua": safe_float(row["agua_kg"]),
        "rheo 1000": safe_float(row["aditivo_rheo_sika115"]),
        "sika 115": safe_float(row["aditivo_rheo_sika115"]),
        "basf 719": safe_float(row["aditivo_basf_sika200"]),
        "sika 200": safe_float(row["aditivo_basf_sika200"]),
        "delvo": safe_float(row["aditivo_delvo"]),
        "masterglenium 7950": safe_float(row["aditivo_glenium_7950"]),
        "masterglenium 7970": safe_float(row["aditivo_glenium_7970"]),
        "sika pp 48-barchip": safe_float(row["aditivo_fibras"]),
    }
    return consumo


def cruzar_consumo_vs_stock(resumen_consumo: dict):
    """
    Cruce:
    - resumen_consumo: dict material_norm -> consumo_total
    Devuelve:
    - filas: lista de resultados
    - no_mapeados: lista de materiales consumo que no se hallaron en catalogo
    - no_encontrados: lista de materiales en catalogo sin consumo (no se usa mucho)
    """
    catalogo = obtener_stock_catalogo()

    filas = []
    no_mapeados = []

    for mat_norm, consumo in resumen_consumo.items():
        c = float(consumo or 0.0)

        if mat_norm not in catalogo:
            no_mapeados.append(mat_norm)
            continue

        it = catalogo[mat_norm]
        stock = float(it.get("stock", 0.0) or 0.0)
        minimo = float(it.get("minimo", 0.0) or 0.0)

        saldo = stock - c
        deficit = 0.0
        if saldo < 0:
            deficit = abs(saldo)

        estado = "OK"
        if saldo < 0:
            estado = "CRITICO"
        elif minimo > 0 and saldo < minimo:
            estado = "BAJO"

        filas.append(
            {
                "material": it["nombre"],
                "unidad": it.get("unidad", ""),
                "stock": stock,
                "minimo": minimo,
                "consumo": c,
                "saldo": saldo,
                "deficit": deficit,
                "estado": estado,
            }
        )

    no_encontrados = []  # reservado por si luego lo necesitas

    # Orden: primero críticos, luego bajos, luego ok
    orden = {"CRITICO": 0, "BAJO": 1, "OK": 2}
    filas.sort(key=lambda x: (orden.get(x["estado"], 9), x["material"].lower()))

    return filas, no_mapeados, no_encontrados


def insertar_material(material, stock, unidad, minimo):
    """
    Inserta material y crea movimiento inicial.
    IMPORTANTE: si la tabla materiales NO tiene columna minimo, no reventamos.
    """
    if not material or not isinstance(material, str):
        print("Error: Nombre de material inválido o vacío")
        return None

    if not unidad or not isinstance(unidad, str):
        print("Error: Unidad inválida o vacía")
        return None

    try:
        stock = float(stock)
    except (ValueError, TypeError):
        print("Error: Stock o mínimo deben ser valores numéricos")
        return None

    if stock < 0:
        print(f"Error: El stock no puede ser negativo. Recibido: {stock}")
        return None

    if minimo < 0:
        print(f"Error: El mínimo no puede ser negativo. Recibido: {minimo}")
        return None

    try:
        conn = obtener_conexion_autonoma()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM materiales WHERE nombre = ?", (material,))
        if cursor.fetchone():
            print(f"Error: El material '{material}' ya existe en la base de datos")
            conn.close()
            return None

        cols = set(obtener_columnas_tabla("materiales"))
        # Insert flexible según columnas reales
        if "minimo" in cols:
            query_materiales = "INSERT INTO materiales (nombre, unidad, minimo) VALUES (?, ?, ?)"
            cursor.execute(query_materiales, (material, unidad, minimo))
        else:
            query_materiales = "INSERT INTO materiales (nombre, unidad) VALUES (?, ?)"
            cursor.execute(query_materiales, (material, unidad))

        material_id = cursor.lastrowid

        # Movimiento inicial de ingreso
        fecha = date.today().isoformat()
        usuario_id = 1
        tipo = "INGRESO"
        proveedor = "Desconocido"

        query_movimientos = """
            INSERT INTO movimientos (usuario_id, material_id, cantidad, fecha, tipo, proveedor)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query_movimientos, (usuario_id, material_id, stock, fecha, tipo, proveedor))

        conn.commit()
        conn.close()
        return material_id

    except sqlite3.Error as e:
        print(f"Error al insertar material: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return None
