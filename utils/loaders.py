import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


# -------------------------
# DB helpers
# -------------------------
def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_path() -> str:
    """
    Usa:
    - ENV DATABASE (opcional)
    - Si no, db/gestion_materiales.db relativo al proyecto
    """
    env = os.environ.get("DATABASE")
    if env and os.path.exists(env):
        return env

    default = os.path.join(_base_dir(), "db", "gestion_materiales.db")
    return default


def _connect():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def obtener_columnas_tabla(tabla: str) -> List[str]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({tabla})")
    rows = cur.fetchall()
    conn.close()
    return [r["name"] for r in rows]


# -------------------------
# Dashboard helpers
# -------------------------
def consumo_diario() -> List[Dict[str, Any]]:
    """
    Devuelve consumo/volumen por dia para dashboard.
    (Si tu dashboard usa otra estructura, ajustamos luego,
     pero esto te da un resumen estable.)
    """
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT fecha, SUM(COALESCE(volumen_m3,0)) AS volumen_m3
        FROM despachos
        GROUP BY fecha
        ORDER BY fecha
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def registros_ultima_semana() -> Tuple[List[Dict[str, Any]], int]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM despachos
        WHERE fecha >= date('now','-7 day')
        ORDER BY fecha DESC, id DESC
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows, len(rows)


# -------------------------
# Insert despacho (REGISTRO)
# -------------------------
def insertar_despacho(
    fecha: str,
    volumen: float,
    diseno_mezcla: str,
    wbs: str = "",
    destino: str = "",
    turno: str = "",
    humedad_arena: float = 0,
    asentamiento_final: float = 0,
    temperatura: float = 0,
    lote: str = "",
    fuente_cemento: str = "",
) -> Optional[int]:
    """
    Inserta SOLO campos que pertenecen a tabla despachos.
    NO inserta consumos/recetas (se calculan via JOIN recetas).

    Retorna new_id o None si falla.
    """
    conn = _connect()
    cur = conn.cursor()

    cols = set(obtener_columnas_tabla("despachos"))

    # Campos base que tu app usa
    payload = {
        "fecha": fecha,
        "fuente_cemento": fuente_cemento,
        "diseno_mezcla": diseno_mezcla,
        "lote": lote,
        "zona": destino,
        "wbs": wbs,
        "volumen_m3": volumen,
        "turno": turno,
        "arena_humedad_pct": humedad_arena,
        "asentamiento_final_cm": asentamiento_final,
        "temperatura_c": temperatura,
    }

    # Filtra solo columnas existentes (para que nunca reviente por "no such column")
    payload = {k: v for k, v in payload.items() if k in cols}

    if "fecha" not in payload or "diseno_mezcla" not in payload or "volumen_m3" not in payload:
        conn.close()
        return None

    campos = list(payload.keys())
    placeholders = ",".join(["?"] * len(campos))
    sql = f"INSERT INTO despachos ({','.join(campos)}) VALUES ({placeholders})"

    try:
        cur.execute(sql, [payload[c] for c in campos])
        conn.commit()
        new_id = int(cur.lastrowid)
        conn.close()
        return new_id
    except Exception:
        conn.rollback()
        conn.close()
        return None


# -------------------------
# Historial + Consumo estimado (JOIN recetas)
# -------------------------
def _build_filters(
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    where = []
    args: List[Any] = []

    if diseno:
        where.append("d.diseno_mezcla = ?")
        args.append(diseno)

    if zona:
        where.append("d.zona LIKE ?")
        args.append(f"%{zona}%")

    if turno:
        where.append("d.turno = ?")
        args.append(turno)

    if wbs:
        where.append("d.wbs LIKE ?")
        args.append(f"%{wbs}%")

    sql_where = ""
    if where:
        sql_where = " AND " + " AND ".join(where)

    return sql_where, args


def obtener_historial_consumo(
    inicio: str,
    fin: str,
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Devuelve filas de despachos + columnas estimadas:
    est_arena_kg, est_grava_kg, est_cemento_he_kg, est_cemento_ip_kg, est_agua_kg,
    est_aditivos...
    """
    sql_where, extra_args = _build_filters(diseno=diseno, zona=zona, turno=turno, wbs=wbs)

    conn = _connect()
    cur = conn.cursor()

    # Nota:
    # recetas tiene cemento_kg (no he/ip). Nosotros lo partimos para mostrar:
    # HE = 60% , IP = 40% (si quieres otro split, me dices y lo cambio).
    cur.execute(
        f"""
        SELECT
            d.id,
            d.fecha,
            d.fuente_cemento,
            d.diseno_mezcla,
            d.lote,
            d.zona,
            d.wbs,
            d.volumen_m3,
            d.turno,
            d.arena_humedad_pct,
            d.asentamiento_final_cm,
            d.temperatura_c,

            -- estimados por receta (si no hay receta, quedan NULL y luego los tratamos)
            (d.volumen_m3 * r.arena_kg) AS est_arena_kg,
            (d.volumen_m3 * r.grava_kg) AS est_grava_kg,
            (d.volumen_m3 * r.cemento_kg * 0.60) AS est_cemento_he_kg,
            (d.volumen_m3 * r.cemento_kg * 0.40) AS est_cemento_ip_kg,
            (d.volumen_m3 * r.agua_kg) AS est_agua_kg,

            (d.volumen_m3 * r.aditivo_rheo_sika115) AS est_aditivo_rheo_sika115,
            (d.volumen_m3 * r.aditivo_basf_sika200) AS est_aditivo_basf_sika200,
            (d.volumen_m3 * r.aditivo_delvo) AS est_aditivo_delvo,
            (d.volumen_m3 * r.aditivo_glenium_7950) AS est_aditivo_glenium_7950,
            (d.volumen_m3 * r.aditivo_glenium_7970) AS est_aditivo_glenium_7970,
            (d.volumen_m3 * r.aditivo_fibras) AS est_aditivo_fibras

        FROM despachos d
        LEFT JOIN recetas r
               ON r.codigo_diseno = d.diseno_mezcla
        WHERE d.fecha >= ? AND d.fecha <= ?
        {sql_where}
        ORDER BY d.fecha ASC, d.id ASC
        """,
        [inicio, fin] + extra_args,
    )

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def cruce_consumo_por_rango(
    inicio: str,
    fin: str,
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retorna resumen de consumo estimado TOTAL en el rango.
    """
    filas = obtener_historial_consumo(inicio, fin, diseno=diseno, zona=zona, turno=turno, wbs=wbs)

    resumen = {
        "arena_kg": 0.0,
        "grava_kg": 0.0,
        "cemento_he_kg": 0.0,
        "cemento_ip_kg": 0.0,
        "agua_kg": 0.0,
        "aditivo_rheo_sika115": 0.0,
        "aditivo_basf_sika200": 0.0,
        "aditivo_delvo": 0.0,
        "aditivo_glenium_7950": 0.0,
        "aditivo_glenium_7970": 0.0,
        "aditivo_fibras": 0.0,
        "_errores": 0,
    }

    for f in filas:
        # si no hay receta, est_* vienen None
        if f.get("est_arena_kg") is None and f.get("est_grava_kg") is None:
            resumen["_errores"] += 1
            continue

        resumen["arena_kg"] += float(f.get("est_arena_kg") or 0)
        resumen["grava_kg"] += float(f.get("est_grava_kg") or 0)
        resumen["cemento_he_kg"] += float(f.get("est_cemento_he_kg") or 0)
        resumen["cemento_ip_kg"] += float(f.get("est_cemento_ip_kg") or 0)
        resumen["agua_kg"] += float(f.get("est_agua_kg") or 0)

        resumen["aditivo_rheo_sika115"] += float(f.get("est_aditivo_rheo_sika115") or 0)
        resumen["aditivo_basf_sika200"] += float(f.get("est_aditivo_basf_sika200") or 0)
        resumen["aditivo_delvo"] += float(f.get("est_aditivo_delvo") or 0)
        resumen["aditivo_glenium_7950"] += float(f.get("est_aditivo_glenium_7950") or 0)
        resumen["aditivo_glenium_7970"] += float(f.get("est_aditivo_glenium_7970") or 0)
        resumen["aditivo_fibras"] += float(f.get("est_aditivo_fibras") or 0)

    return resumen


# -------------------------
# Inventario / stock
# -------------------------
def obtener_materiales() -> List[Dict[str, Any]]:
    """
    Lee materiales sin asumir el nombre exacto del minimo.
    Normaliza a llave: minimo
    """
    cols = set(obtener_columnas_tabla("materiales"))

    candidato_minimos = ["minimo", "minimo_stock", "stock_minimo", "min_stock", "min"]
    col_min = next((c for c in candidato_minimos if c in cols), None)

    base_cols = ["id", "nombre", "unidad"]
    select_cols = base_cols.copy()
    if col_min:
        select_cols.append(col_min)

    conn = _connect()
    cur = conn.cursor()
    cur.execute(f"SELECT {', '.join(select_cols)} FROM materiales ORDER BY nombre")
    rows = cur.fetchall()
    conn.close()

    out: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        minimo = 0
        if col_min:
            minimo = d.get(col_min, 0) if d.get(col_min) is not None else 0
            if col_min != "minimo":
                d.pop(col_min, None)

        out.append(
            {
                "id": d.get("id"),
                "nombre": d.get("nombre", ""),
                "unidad": d.get("unidad", ""),
                "minimo": float(minimo or 0),
            }
        )
    return out


def obtener_stock_catalogo() -> List[Dict[str, Any]]:
    """
    Stock actual = sum(entradas) - sum(salidas) en tabla movimientos.
    """
    materiales = obtener_materiales()

    conn = _connect()
    cur = conn.cursor()

    # intentamos detectar nombre de columna tipo
    mov_cols = set(obtener_columnas_tabla("movimientos"))
    col_tipo = "tipo" if "tipo" in mov_cols else None

    out = []
    for m in materiales:
        mid = m["id"]

        if col_tipo:
            cur.execute(
                """
                SELECT
                  SUM(CASE WHEN tipo='Entrada' THEN COALESCE(cantidad,0) ELSE 0 END) AS entradas,
                  SUM(CASE WHEN tipo='Salida' THEN COALESCE(cantidad,0) ELSE 0 END) AS salidas
                FROM movimientos
                WHERE material_id = ?
                """,
                [mid],
            )
        else:
            # fallback: si no hay columna tipo, asumimos cantidad neta
            cur.execute(
                "SELECT SUM(COALESCE(cantidad,0)) AS neto FROM movimientos WHERE material_id = ?",
                [mid],
            )

        r = cur.fetchone()
        if col_tipo:
            entradas = float(r["entradas"] or 0)
            salidas = float(r["salidas"] or 0)
            stock = entradas - salidas
        else:
            stock = float(r["neto"] or 0)

        out.append(
            {
                "id": mid,
                "material": m["nombre"],
                "unidad": m["unidad"],
                "minimo": float(m["minimo"] or 0),
                "stock_actual": stock,
            }
        )

    conn.close()
    return out


def cruzar_consumo_vs_stock(resumen_consumo: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Cruza resumen_consumo vs stock de materiales.
    Devuelve:
      filas: [{material, unidad, stock_actual, minimo, consumo_estimado, deficit_sugerido, bajo_minimo}]
      no_mapeados: [campos consumo sin mapeo]
      no_encontrados: [materiales mapeados que no existen]
    """

    # Mapeo consumo -> nombre material (debe coincidir con materiales.nombre)
    # Ajusta los nombres EXACTOS a como tengas tus materiales cargados.
    mapping = {
        "arena_kg": "Arena",
        "grava_kg": "Grava",
        "cemento_he_kg": "Cemento HE",
        "cemento_ip_kg": "Cemento IP",
        "agua_kg": "Agua",
        "aditivo_rheo_sika115": "RHEO 1000 + Sika 115",
        "aditivo_basf_sika200": "BASF 719 + Sika 200",
        "aditivo_delvo": "Delvo",
        "aditivo_glenium_7950": "MasterGlenium 7950",
        "aditivo_glenium_7970": "MasterGlenium 7970",
        "aditivo_fibras": "Sika PP 48 - Barchip",
    }

    catalogo = obtener_stock_catalogo()
    idx = {c["material"]: c for c in catalogo}

    filas = []
    no_mapeados = []
    no_encontrados = []

    for k, v in resumen_consumo.items():
        if k.startswith("_"):
            continue

        if k not in mapping:
            no_mapeados.append(k)
            continue

        nombre_mat = mapping[k]
        if nombre_mat not in idx:
            no_encontrados.append(nombre_mat)
            continue

        item = idx[nombre_mat]
        consumo = float(v or 0)
        stock = float(item["stock_actual"] or 0)
        minimo = float(item["minimo"] or 0)

        deficit = max(consumo - stock, 0)
        bajo_minimo = stock < minimo

        filas.append(
            {
                "material": nombre_mat,
                "unidad": item["unidad"],
                "stock_actual": stock,
                "minimo": minimo,
                "consumo_estimado": consumo,
                "deficit_sugerido": deficit,
                "bajo_minimo": bajo_minimo,
            }
        )

    # orden: deficit desc, luego bajo minimo
    filas.sort(key=lambda x: (x["deficit_sugerido"], x["bajo_minimo"]), reverse=True)

    return filas, no_mapeados, no_encontrados
