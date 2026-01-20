import os
import sqlite3
from datetime import datetime, timedelta, date


# -----------------------------
# Conexion / helpers
# -----------------------------
def obtener_conexion_autonoma():
    db_path = os.environ.get("DATABASE")
    if not db_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, "db", "gestion_materiales.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def obtener_columnas_tabla(nombre_tabla: str):
    conn = obtener_conexion_autonoma()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({nombre_tabla})")
    cols = [r["name"] for r in cur.fetchall()]
    conn.close()
    return cols


def _safe_float(x):
    try:
        return float(x) if x is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _safe_str(x):
    return (x or "").strip()


def _tabla_tiene_columna(tabla: str, col: str) -> bool:
    try:
        return col in set(obtener_columnas_tabla(tabla))
    except Exception:
        return False


# -----------------------------
# Dashboard
# -----------------------------
def consumo_diario():
    """
    Retorna consumo/produccion del dia actual (segun tabla despachos).
    """
    conn = obtener_conexion_autonoma()
    cur = conn.cursor()

    hoy = date.today().isoformat()

    cur.execute(
        """
        SELECT
            COUNT(*) AS registros,
            COALESCE(SUM(volumen_m3), 0) AS volumen_m3
        FROM despachos
        WHERE fecha = ?
        """,
        (hoy,),
    )
    row = cur.fetchone()
    conn.close()

    return {
        "fecha": hoy,
        "registros": int(row["registros"] or 0),
        "volumen_m3": _safe_float(row["volumen_m3"]),
    }


def registros_ultima_semana():
    """
    Lista volumen por dia ultimos 7 dias + total de registros.
    """
    conn = obtener_conexion_autonoma()
    cur = conn.cursor()

    fin = date.today()
    inicio = fin - timedelta(days=6)

    cur.execute(
        """
        SELECT
            fecha,
            COUNT(*) AS registros,
            COALESCE(SUM(volumen_m3), 0) AS volumen_m3
        FROM despachos
        WHERE fecha BETWEEN ? AND ?
        GROUP BY fecha
        ORDER BY fecha
        """,
        (inicio.isoformat(), fin.isoformat()),
    )
    rows = cur.fetchall()

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM despachos
        WHERE fecha BETWEEN ? AND ?
        """,
        (inicio.isoformat(), fin.isoformat()),
    )
    total = cur.fetchone()["total"]

    conn.close()

    data = []
    for r in rows:
        data.append(
            {
                "fecha": r["fecha"],
                "registros": int(r["registros"] or 0),
                "volumen_m3": _safe_float(r["volumen_m3"]),
            }
        )

    return data, int(total or 0)


# -----------------------------
# Insertar despacho (registro diario)
# -----------------------------
def insertar_despacho(
    fecha,
    volumen,
    diseno_mezcla,
    wbs=None,
    destino=None,
    turno=None,
    humedad_arena=None,
    asentamiento_final=None,
    temperatura=None,
    fuente_cemento=None,
):
    """
    Inserta un despacho calculando consumos a partir de recetas.

    IMPORTANTE (segun tu SQLite real):
    - despachos tiene cemento_kg (NO cemento_he_kg / cemento_ip_kg)
    - despachos SI tiene fuente_cemento
    - recetas tiene cemento_kg y aditivo_a / aditivo_b
      que mapeamos a:
        aditivo_a -> aditivo_rheo_sika115
        aditivo_b -> aditivo_basf_sika200
    """
    fecha = _safe_str(fecha)
    diseno_mezcla = _safe_str(diseno_mezcla)
    if not fecha or not diseno_mezcla:
        return None

    try:
        volumen = float(volumen)
    except (ValueError, TypeError):
        return None
    if volumen <= 0:
        return None

    wbs = _safe_str(wbs) or None
    destino = _safe_str(destino) or None
    turno = _safe_str(turno) or None

    try:
        humedad_arena = float(humedad_arena) if humedad_arena is not None else None
    except (ValueError, TypeError):
        humedad_arena = None

    try:
        asentamiento_final = float(asentamiento_final) if asentamiento_final is not None else None
    except (ValueError, TypeError):
        asentamiento_final = None

    try:
        temperatura = float(temperatura) if temperatura is not None else None
    except (ValueError, TypeError):
        temperatura = None

    fuente_cemento = _safe_str(fuente_cemento) or "HE"  # default

    conn = obtener_conexion_autonoma()
    cur = conn.cursor()

    # Cargar receta por codigo_diseno
    cur.execute(
        """
        SELECT
            codigo_diseno,
            COALESCE(arena_kg,0) AS arena_kg,
            COALESCE(grava_kg,0) AS grava_kg,
            COALESCE(cemento_kg,0) AS cemento_kg,
            COALESCE(agua_kg,0) AS agua_kg,
            COALESCE(aditivo_a,0) AS aditivo_a,
            COALESCE(aditivo_b,0) AS aditivo_b,
            COALESCE(aditivo_delvo,0) AS aditivo_delvo,
            COALESCE(aditivo_glenium_7950,0) AS aditivo_glenium_7950,
            COALESCE(aditivo_glenium_7970,0) AS aditivo_glenium_7970,
            COALESCE(aditivo_fibras,0) AS aditivo_fibras
        FROM recetas
        WHERE codigo_diseno = ?
        """,
        (diseno_mezcla,),
    )
    receta = cur.fetchone()
    if not receta:
        conn.close()
        return None

    # Receta se asume por m3: total = receta * volumen
    arena_kg = _safe_float(receta["arena_kg"]) * volumen
    grava_kg = _safe_float(receta["grava_kg"]) * volumen
    cemento_kg = _safe_float(receta["cemento_kg"]) * volumen
    agua_kg = _safe_float(receta["agua_kg"]) * volumen

    # Mapear aditivos de recetas -> columnas reales en despachos
    aditivo_rheo_sika115 = _safe_float(receta["aditivo_a"]) * volumen
    aditivo_basf_sika200 = _safe_float(receta["aditivo_b"]) * volumen
    aditivo_delvo = _safe_float(receta["aditivo_delvo"]) * volumen
    aditivo_glenium_7950 = _safe_float(receta["aditivo_glenium_7950"]) * volumen
    aditivo_glenium_7970 = _safe_float(receta["aditivo_glenium_7970"]) * volumen
    aditivo_fibras = _safe_float(receta["aditivo_fibras"]) * volumen

    try:
        cur.execute(
            """
            INSERT INTO despachos (
                fecha, fuente_cemento, diseno_mezcla, lote, zona, wbs, volumen_m3, turno,
                arena_humedad_pct, asentamiento_final_cm, temperatura_c,
                arena_kg, grava_kg, cemento_kg, agua_kg,
                aditivo_rheo_sika115, aditivo_basf_sika200, aditivo_delvo,
                aditivo_glenium_7950, aditivo_glenium_7970, aditivo_fibras
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                fecha, fuente_cemento, diseno_mezcla, None, destino, wbs, volumen, turno,
                humedad_arena, asentamiento_final, temperatura,
                arena_kg, grava_kg, cemento_kg, agua_kg,
                aditivo_rheo_sika115, aditivo_basf_sika200, aditivo_delvo,
                aditivo_glenium_7950, aditivo_glenium_7970, aditivo_fibras
            ),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return new_id
    except Exception:
        conn.rollback()
        conn.close()
        return None


# -----------------------------
# Historial (filas para historial.js)
# -----------------------------
def obtener_historial_consumo(
    inicio,
    fin,
    diseno=None,
    zona=None,
    turno=None,
    wbs=None,
):
    """
    Devuelve filas con llaves que tu historial.js usa:
    fecha, diseno_mezcla, zona, wbs, turno, volumen_m3,
    est_arena_kg, est_grava_kg, est_cemento_he_kg, est_cemento_ip_kg, est_agua_kg,
    est_rheo_sika115, est_basf_sika200, est_delvo, est_glenium_7950, est_glenium_7970, est_fibras
    """
    inicio = _safe_str(inicio)
    fin = _safe_str(fin)
    if not inicio or not fin:
        return []

    params = [inicio, fin]
    where = ["d.fecha BETWEEN ? AND ?"]

    if diseno:
        where.append("d.diseno_mezcla = ?")
        params.append(diseno)
    if zona:
        where.append("d.zona = ?")
        params.append(zona)
    if turno:
        where.append("d.turno = ?")
        params.append(turno)
    if wbs:
        where.append("d.wbs = ?")
        params.append(wbs)

    where_sql = " AND ".join(where)

    conn = obtener_conexion_autonoma()
    cur = conn.cursor()

    # Cemento se guarda como cemento_kg + fuente_cemento (HE/IP)
    # Para mantener tu front (Cem HE / Cem IP), lo separamos por fuente.
    cur.execute(
        f"""
        SELECT
            d.id,
            d.fecha,
            d.diseno_mezcla,
            COALESCE(d.zona,'') AS zona,
            COALESCE(d.wbs,'') AS wbs,
            COALESCE(d.turno,'') AS turno,
            COALESCE(d.volumen_m3,0) AS volumen_m3,

            COALESCE(d.arena_kg,0) AS est_arena_kg,
            COALESCE(d.grava_kg,0) AS est_grava_kg,
            CASE WHEN UPPER(COALESCE(d.fuente_cemento,'HE')) = 'IP'
                 THEN 0 ELSE COALESCE(d.cemento_kg,0) END AS est_cemento_he_kg,
            CASE WHEN UPPER(COALESCE(d.fuente_cemento,'HE')) = 'IP'
                 THEN COALESCE(d.cemento_kg,0) ELSE 0 END AS est_cemento_ip_kg,
            COALESCE(d.agua_kg,0) AS est_agua_kg,

            COALESCE(d.aditivo_rheo_sika115,0) AS est_rheo_sika115,
            COALESCE(d.aditivo_basf_sika200,0) AS est_basf_sika200,
            COALESCE(d.aditivo_delvo,0) AS est_delvo,
            COALESCE(d.aditivo_glenium_7950,0) AS est_glenium_7950,
            COALESCE(d.aditivo_glenium_7970,0) AS est_glenium_7970,
            COALESCE(d.aditivo_fibras,0) AS est_fibras,

            COALESCE(d.arena_humedad_pct,0) AS humedad_pct,
            COALESCE(d.asentamiento_final_cm,0) AS asentamiento_cm,
            COALESCE(d.temperatura_c,0) AS temp_c
        FROM despachos d
        WHERE {where_sql}
        ORDER BY d.fecha DESC, d.id DESC
        """,
        params,
    )

    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        out.append({k: r[k] for k in r.keys()})
    return out


# -----------------------------
# Resumen por rango (para alertas/graficas)
# -----------------------------
def cruce_consumo_por_rango(inicio, fin, diseno=None, zona=None, turno=None, wbs=None):
    """
    Retorna un dict material_norm -> consumo_total
    (Este dict es el que cruzar_consumo_vs_stock consume)
    """
    inicio = _safe_str(inicio)
    fin = _safe_str(fin)
    if not inicio or not fin:
        return {}

    params = [inicio, fin]
    where = ["fecha BETWEEN ? AND ?"]

    if diseno:
        where.append("diseno_mezcla = ?")
        params.append(diseno)
    if zona:
        where.append("zona = ?")
        params.append(zona)
    if turno:
        where.append("turno = ?")
        params.append(turno)
    if wbs:
        where.append("wbs = ?")
        params.append(wbs)

    where_sql = " AND ".join(where)

    conn = obtener_conexion_autonoma()
    cur = conn.cursor()

    # cemento: se suma cemento_kg y se separa por fuente_cemento
    cur.execute(
        f"""
        SELECT
            COALESCE(SUM(arena_kg),0) AS arena_kg,
            COALESCE(SUM(grava_kg),0) AS grava_kg,
            COALESCE(SUM(cemento_kg),0) AS cemento_total_kg,
            COALESCE(SUM(CASE WHEN UPPER(COALESCE(fuente_cemento,'HE'))='IP' THEN cemento_kg ELSE 0 END),0) AS cemento_ip_kg,
            COALESCE(SUM(CASE WHEN UPPER(COALESCE(fuente_cemento,'HE'))='IP' THEN 0 ELSE cemento_kg END),0) AS cemento_he_kg,
            COALESCE(SUM(agua_kg),0) AS agua_kg,

            COALESCE(SUM(aditivo_rheo_sika115),0) AS aditivo_rheo_sika115,
            COALESCE(SUM(aditivo_basf_sika200),0) AS aditivo_basf_sika200,
            COALESCE(SUM(aditivo_delvo),0) AS aditivo_delvo,
            COALESCE(SUM(aditivo_glenium_7950),0) AS aditivo_glenium_7950,
            COALESCE(SUM(aditivo_glenium_7970),0) AS aditivo_glenium_7970,
            COALESCE(SUM(aditivo_fibras),0) AS aditivo_fibras
        FROM despachos
        WHERE {where_sql}
        """,
        params,
    )
    row = cur.fetchone()
    conn.close()

    consumo = {
        "arena": _safe_float(row["arena_kg"]),
        "grava": _safe_float(row["grava_kg"]),
        "cemento he": _safe_float(row["cemento_he_kg"]),
        "cemento ip": _safe_float(row["cemento_ip_kg"]),
        "agua": _safe_float(row["agua_kg"]),
        "rheo 1000": _safe_float(row["aditivo_rheo_sika115"]),
        "sika 115": _safe_float(row["aditivo_rheo_sika115"]),
        "basf 719": _safe_float(row["aditivo_basf_sika200"]),
        "sika 200": _safe_float(row["aditivo_basf_sika200"]),
        "delvo": _safe_float(row["aditivo_delvo"]),
        "masterglenium 7950": _safe_float(row["aditivo_glenium_7950"]),
        "masterglenium 7970": _safe_float(row["aditivo_glenium_7970"]),
        "sika pp 48-barchip": _safe_float(row["aditivo_fibras"]),
    }
    return consumo


# -----------------------------
# Stock / inventario desde DB
# -----------------------------
def obtener_stock_catalogo():
    """
    Retorna un catalogo normalizado para cruce consumo vs stock.
    Lee de:
      - materiales (nombre, unidad, minimo?) y
      - stock (material_id, cantidad) si existe
    """
    conn = obtener_conexion_autonoma()
    cur = conn.cursor()

    cols_materiales = set(obtener_columnas_tabla("materiales"))
    cols_stock = set(obtener_columnas_tabla("stock")) if _tabla_tiene_columna("stock", "material_id") else set()

    # materiales
    if "minimo" in cols_materiales:
        cur.execute("SELECT id, nombre, unidad, COALESCE(minimo,0) AS minimo FROM materiales")
    else:
        cur.execute("SELECT id, nombre, unidad, 0 AS minimo FROM materiales")
    mats = cur.fetchall()

    # stock
    stock_map = {}
    if cols_stock and ("cantidad" in cols_stock):
        cur.execute("SELECT material_id, COALESCE(cantidad,0) AS cantidad FROM stock")
        for r in cur.fetchall():
            stock_map[int(r["material_id"])] = _safe_float(r["cantidad"])

    conn.close()

    def norm(s: str):
        return (s or "").strip().lower()

    catalogo = {}
    for m in mats:
        mid = int(m["id"])
        nombre = m["nombre"]
        catalogo[norm(nombre)] = {
            "id": mid,
            "nombre": nombre,
            "unidad": m["unidad"],
            "minimo": _safe_float(m["minimo"]),
            "stock": stock_map.get(mid, 0.0),
        }

    return catalogo


def cruzar_consumo_vs_stock(resumen_consumo: dict):
    """
    Cruce:
    - resumen_consumo: dict material_norm -> consumo_total
    Devuelve:
    - filas
    - no_mapeados
    - no_encontrados (reservado)
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
        deficit = abs(saldo) if saldo < 0 else 0.0

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

    no_encontrados = []

    orden = {"CRITICO": 0, "BAJO": 1, "OK": 2}
    filas.sort(key=lambda x: (orden.get(x["estado"], 9), x["material"].lower()))

    return filas, no_mapeados, no_encontrados
