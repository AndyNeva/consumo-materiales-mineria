# utils/loaders.py
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = "db/gestion_materiales.db"


# -------------------------
# Helpers
# -------------------------
def _connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r["name"] for r in cur.fetchall()]


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        return default


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    """
    Acceso seguro compatible con sqlite3.Row y dict.
    """
    if row is None:
        return default
    try:
        # sqlite3.Row soporta row["col"]
        return row[key]
    except Exception:
        # si fuese dict u otro
        try:
            return row.get(key, default)  # type: ignore[attr-defined]
        except Exception:
            return default


def _first_existing_column(cols: List[str], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in cols:
            return c
    return None


def _receta_por_diseno(conn: sqlite3.Connection, diseno: str) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM recetas WHERE codigo_diseno = ? LIMIT 1", (diseno,))
    return cur.fetchone()


def _material_row_by_nombre(conn: sqlite3.Connection, nombre: str) -> Optional[sqlite3.Row]:
    # En tu DB real la columna es "nombre"
    cur = conn.execute("SELECT * FROM materiales WHERE LOWER(nombre)=LOWER(?) LIMIT 1", (nombre,))
    return cur.fetchone()


def _calc_consumos_estimados(receta: sqlite3.Row, volumen_m3: float) -> Dict[str, float]:
    arena = _safe_float(_row_value(receta, "arena_kg", 0.0)) * volumen_m3
    grava = _safe_float(_row_value(receta, "grava_kg", 0.0)) * volumen_m3
    agua = _safe_float(_row_value(receta, "agua_kg", 0.0)) * volumen_m3
    cemento = _safe_float(_row_value(receta, "cemento_kg", 0.0)) * volumen_m3

    rheo = _safe_float(_row_value(receta, "aditivo_rheo_sika115", 0.0)) * volumen_m3
    basf = _safe_float(_row_value(receta, "aditivo_basf_sika200", 0.0)) * volumen_m3
    delvo = _safe_float(_row_value(receta, "aditivo_delvo", 0.0)) * volumen_m3
    gl7950 = _safe_float(_row_value(receta, "aditivo_glenium_7950", 0.0)) * volumen_m3
    gl7970 = _safe_float(_row_value(receta, "aditivo_glenium_7970", 0.0)) * volumen_m3
    fibras = _safe_float(_row_value(receta, "aditivo_fibras", 0.0)) * volumen_m3

    return {
        "arena_kg": arena,
        "grava_kg": grava,
        "agua_kg": agua,
        "cemento_kg": cemento,
        "aditivo_rheo_sika115": rheo,
        "aditivo_basf_sika200": basf,
        "aditivo_delvo": delvo,
        "aditivo_glenium_7950": gl7950,
        "aditivo_glenium_7970": gl7970,
        "aditivo_fibras": fibras,
    }


def _compat_front_from_row(d: Dict[str, Any]) -> Dict[str, Any]:
    d["est_arena_kg"] = d.get("arena_kg")
    d["est_grava_kg"] = d.get("grava_kg")
    d["est_agua_kg"] = d.get("agua_kg")

    cemento = _safe_float(d.get("cemento_kg"), 0.0)
    d["est_cemento_he_kg"] = cemento
    d["est_cemento_ip_kg"] = 0.0

    d["est_aditivo_rheo_sika115"] = d.get("aditivo_rheo_sika115")
    d["est_aditivo_basf_sika200"] = d.get("aditivo_basf_sika200")
    d["est_aditivo_delvo"] = d.get("aditivo_delvo")
    d["est_aditivo_glenium_7950"] = d.get("aditivo_glenium_7950")
    d["est_aditivo_glenium_7970"] = d.get("aditivo_glenium_7970")
    d["est_aditivo_fibras"] = d.get("aditivo_fibras")

    return d


# -------------------------
# Dashboard
# -------------------------
def consumo_diario(fecha: Optional[str] = None, db_path: str = DB_PATH) -> float:
    if not fecha:
        fecha = date.today().isoformat()

    with _connect(db_path) as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(volumen_m3),0) AS total FROM despachos WHERE fecha = ?",
            (fecha,),
        )
        return float(cur.fetchone()["total"])


def registros_ultima_semana(db_path: str = DB_PATH) -> Tuple[List[Dict[str, Any]], int]:
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            SELECT fecha, diseno_mezcla, zona, wbs, volumen_m3
            FROM despachos
            WHERE fecha >= date('now','-6 day')
            ORDER BY fecha DESC, id DESC
            """
        )
        rows = [dict(r) for r in cur.fetchall()]

        cur2 = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM despachos
            WHERE fecha >= date('now','-6 day')
            """
        )
        n = int(cur2.fetchone()["n"])
        return rows, n


# -------------------------
# Insert despacho (registro diario)
# -------------------------
def insertar_despacho(
    fecha: str,
    volumen: float,
    diseno_mezcla: str,
    wbs: str,
    destino: str,  # -> despachos.zona
    turno: str,
    humedad_arena: Optional[float] = None,
    asentamiento_final: Optional[float] = None,
    temperatura: Optional[float] = None,
    db_path: str = DB_PATH,
) -> Optional[int]:
    try:
        volumen_m3 = float(volumen)
    except Exception:
        return None

    if volumen_m3 <= 0 or not diseno_mezcla:
        return None

    with _connect(db_path) as conn:
        receta = _receta_por_diseno(conn, diseno_mezcla)
        if receta is None:
            return None

        est = _calc_consumos_estimados(receta, volumen_m3)

        data: Dict[str, Any] = {
            "fecha": fecha,
            "volumen_m3": volumen_m3,
            "diseno_mezcla": diseno_mezcla,
            "zona": destino,
            "wbs": wbs,
            "turno": turno,
            "arena_humedad_pct": humedad_arena,
            "asentamiento_final_cm": asentamiento_final,
            "temperatura_c": temperatura,
            **est,
        }

        cols = _table_columns(conn, "despachos")
        data = {k: v for k, v in data.items() if k in cols}

        placeholders = ", ".join(["?"] * len(data))
        col_sql = ", ".join(data.keys())
        sql = f"INSERT INTO despachos ({col_sql}) VALUES ({placeholders})"

        cur = conn.execute(sql, tuple(data.values()))
        conn.commit()
        return int(cur.lastrowid)


# -------------------------
# Historial consumo
# -------------------------
def obtener_historial_consumo(
    inicio: str,
    fin: str,
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    with _connect(db_path) as conn:
        cols = _table_columns(conn, "despachos")

        where = ["fecha >= ? AND fecha <= ?"]
        params: List[Any] = [inicio, fin]

        if diseno:
            where.append("diseno_mezcla = ?")
            params.append(diseno)
        if zona:
            where.append("zona LIKE ?")
            params.append(f"%{zona}%")
        if turno:
            where.append("turno = ?")
            params.append(turno)
        if wbs:
            where.append("wbs LIKE ?")
            params.append(f"%{wbs}%")

        base_select = [
            "id", "fecha", "diseno_mezcla", "zona", "turno", "wbs", "volumen_m3",
            "arena_kg", "grava_kg", "cemento_kg", "agua_kg",
            "aditivo_rheo_sika115", "aditivo_basf_sika200", "aditivo_delvo",
            "aditivo_glenium_7950", "aditivo_glenium_7970", "aditivo_fibras",
            "arena_humedad_pct", "asentamiento_final_cm", "temperatura_c",
        ]
        select_cols = [c for c in base_select if c in cols]

        sql = f"""
            SELECT {", ".join(select_cols)}
            FROM despachos
            WHERE {" AND ".join(where)}
            ORDER BY fecha ASC, id ASC
        """
        cur = conn.execute(sql, params)

        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            d = dict(r)
            out.append(_compat_front_from_row(d))
        return out


def cruce_consumo_por_rango(
    inicio: str,
    fin: str,
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Dict[str, Any]:
    rows = obtener_historial_consumo(inicio, fin, diseno, zona, turno, wbs, db_path=db_path)

    tot: Dict[str, Any] = {
        "registros": len(rows),
        "volumen_m3": 0.0,
        "arena_kg": 0.0,
        "grava_kg": 0.0,
        "agua_kg": 0.0,
        "cemento_kg": 0.0,
        "aditivo_rheo_sika115": 0.0,
        "aditivo_basf_sika200": 0.0,
        "aditivo_delvo": 0.0,
        "aditivo_glenium_7950": 0.0,
        "aditivo_glenium_7970": 0.0,
        "aditivo_fibras": 0.0,
    }

    for r in rows:
        tot["volumen_m3"] += _safe_float(r.get("volumen_m3"))
        tot["arena_kg"] += _safe_float(r.get("arena_kg"))
        tot["grava_kg"] += _safe_float(r.get("grava_kg"))
        tot["agua_kg"] += _safe_float(r.get("agua_kg"))
        tot["cemento_kg"] += _safe_float(r.get("cemento_kg"))
        tot["aditivo_rheo_sika115"] += _safe_float(r.get("aditivo_rheo_sika115"))
        tot["aditivo_basf_sika200"] += _safe_float(r.get("aditivo_basf_sika200"))
        tot["aditivo_delvo"] += _safe_float(r.get("aditivo_delvo"))
        tot["aditivo_glenium_7950"] += _safe_float(r.get("aditivo_glenium_7950"))
        tot["aditivo_glenium_7970"] += _safe_float(r.get("aditivo_glenium_7970"))
        tot["aditivo_fibras"] += _safe_float(r.get("aditivo_fibras"))

    return tot


def cruzar_consumo_vs_stock(
    resumen: Dict[str, Any],
    db_path: str = DB_PATH
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    mapa = [
        ("arena_kg", "Arena", "kg"),
        ("grava_kg", "Grava", "kg"),
        ("cemento_kg", "Cemento", "kg"),
        ("agua_kg", "Agua", "kg"),
        ("aditivo_rheo_sika115", "Rheo+Sika115", "kg"),
        ("aditivo_basf_sika200", "BASF+Sika200", "kg"),
        ("aditivo_delvo", "Delvo", "l"),
        ("aditivo_glenium_7950", "Glenium 7950", "l"),
        ("aditivo_glenium_7970", "Glenium 7970", "l"),
        ("aditivo_fibras", "Fibras", "kg"),
    ]

    no_mapeados: List[str] = []
    no_encontrados: List[str] = []
    out: List[Dict[str, Any]] = []

    with _connect(db_path) as conn:
        mat_cols = _table_columns(conn, "materiales")

        # Candidatos típicos (por si tu tabla usa otros nombres)
        stock_col = _first_existing_column(mat_cols, ["stock_actual", "stock", "existencia", "saldo", "cantidad"])
        min_col = _first_existing_column(mat_cols, ["stock_minimo", "minimo", "stock_min", "min"])

        for campo, nombre, unidad in mapa:
            consumo = _safe_float(resumen.get(campo))

            mat = _material_row_by_nombre(conn, nombre)
            if not mat:
                if consumo > 0:
                    no_encontrados.append(nombre)
                stock = 0.0
                minimo = 0.0
            else:
                stock = _safe_float(_row_value(mat, stock_col, 0.0)) if stock_col else 0.0
                minimo = _safe_float(_row_value(mat, min_col, 0.0)) if min_col else 0.0

            deficit = max(consumo - stock, 0.0)
            bajo_minimo = (stock < minimo) if minimo > 0 else False

            estado = "OK"
            if deficit > 0:
                estado = "Deficit"
            elif bajo_minimo:
                estado = "Bajo minimo"

            out.append({
                "material": nombre,
                "unidad": unidad,
                "stock_actual": stock,
                "minimo": minimo,
                "consumo_estimado": consumo,
                "deficit_sugerido": deficit,
                "bajo_minimo": bajo_minimo,
                "estado": estado,
            })

    mapa_keys = {x[0] for x in mapa}
    for k, v in (resumen or {}).items():
        if k in ("registros", "volumen_m3"):
            continue
        if (k.endswith("_kg") or k.startswith("aditivo_")) and k not in mapa_keys and _safe_float(v) != 0:
            no_mapeados.append(k)

    return out, no_mapeados, no_encontrados
