# utils/loaders.py
import os
import sqlite3
from datetime import date, timedelta


# =========================================================
# Conexión / helpers
# =========================================================
def _db_path() -> str:
    db = os.environ.get("DATABASE")
    if not db:
        raise RuntimeError("DATABASE no está configurado en variables de entorno.")
    return db


def _connect():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _table_cols(conn, table: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return {r[1] for r in cur.fetchall()}


def _has_col(conn, table: str, col: str) -> bool:
    return col in _table_cols(conn, table)


def _obtener_receta_por_codigo(conn, codigo_diseno: str):
    """
    Devuelve Row de recetas o None.

    Esquema posible:
    - arena_kg, grava_kg, cemento_kg, agua_kg
    - aditivo_a, aditivo_b, delvo_l, glenium_7950, glenium_7970, fibras_kg
    y/o columnas nuevas:
    - cemento_he_kg, cemento_ip_kg
    - aditivo_rheo_sika115, aditivo_basf_sika200
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM recetas WHERE codigo_diseno = ?", (codigo_diseno,))
    return cur.fetchone()


def _receta_get(receta_row, key: str, default=0.0) -> float:
    try:
        if receta_row is None:
            return float(default)
        return float(receta_row[key] or 0)
    except Exception:
        return float(default)


# =========================================================
# Dashboard
# =========================================================
def consumo_diario():
    """Suma volumen_m3 de despachos para la fecha de hoy."""
    hoy = date.today().isoformat()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(volumen_m3), 0) AS total FROM despachos WHERE fecha = ?",
            (hoy,),
        )
        return float(cur.fetchone()["total"] or 0)
    finally:
        conn.close()


def registros_ultima_semana():
    """Retorna (lista_registros, cantidad)."""
    hoy = date.today()
    inicio = (hoy - timedelta(days=6)).isoformat()
    fin = hoy.isoformat()

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT fecha, diseno_mezcla, zona, wbs, turno, volumen_m3
            FROM despachos
            WHERE fecha BETWEEN ? AND ?
            ORDER BY fecha DESC
            """,
            (inicio, fin),
        )
        rows = [dict(r) for r in cur.fetchall()]
        return rows, len(rows)
    finally:
        conn.close()


# =========================================================
# Inserción de despacho
# =========================================================
def insertar_despacho(
    fecha: str,
    volumen: float,
    diseno_mezcla: str,
    wbs: str,
    destino: str,
    turno: str,
    humedad_arena: float = 0,
    asentamiento_final: float = 0,
    temperatura: float = 0,
):
    """
    Inserta un despacho en la tabla despachos.

    - Calcula consumos estimados a partir de la receta * volumen.
    - Inserta en columnas nuevas si existen (cemento_he_kg, aditivo_rheo_sika115, etc.)
      y en columnas antiguas si existen (cemento_kg, aditivo_kg).
    - Retorna id insertado o None.
    """
    if not fecha or not diseno_mezcla:
        return None

    try:
        volumen = float(volumen)
        if volumen <= 0:
            return None
    except Exception:
        return None

    conn = _connect()
    try:
        # Validación receta
        receta = _obtener_receta_por_codigo(conn, diseno_mezcla)
        if not receta:
            return None

    
        cols_d = _table_cols(conn, "despachos")
        cols_r = _table_cols(conn, "recetas")

        # Base por m3
        arena_m3 = _receta_get(receta, "arena_kg", 0.0)
        grava_m3 = _receta_get(receta, "grava_kg", 0.0)
        agua_m3 = _receta_get(receta, "agua_kg", 0.0)

        # Cementos 
        if "cemento_he_kg" in cols_r:
            cemento_he_m3 = _receta_get(receta, "cemento_he_kg", 0.0)
        else:
            cemento_he_m3 = _receta_get(receta, "cemento_kg", 0.0)

        if "cemento_ip_kg" in cols_r:
            cemento_ip_m3 = _receta_get(receta, "cemento_ip_kg", 0.0)
        else:
            cemento_ip_m3 = 0.0

        # Aditivos 
        if "aditivo_rheo_sika115" in cols_r:
            rheo_sika115_m3 = _receta_get(receta, "aditivo_rheo_sika115", 0.0)
        else:
            rheo_sika115_m3 = _receta_get(receta, "aditivo_a", 0.0)

        if "aditivo_basf_sika200" in cols_r:
            basf_sika200_m3 = _receta_get(receta, "aditivo_basf_sika200", 0.0)
        else:
            basf_sika200_m3 = _receta_get(receta, "aditivo_b", 0.0)

        delvo_m3 = _receta_get(receta, "delvo_l", 0.0) 
        g7950_m3 = _receta_get(receta, "glenium_7950", 0.0)
        g7970_m3 = _receta_get(receta, "glenium_7970", 0.0)
        fibras_m3 = _receta_get(receta, "fibras_kg", 0.0)

        # Totales por despacho
        arena_kg = volumen * arena_m3
        grava_kg = volumen * grava_m3
        agua_kg = volumen * agua_m3

        cemento_he_kg = volumen * cemento_he_m3
        cemento_ip_kg = volumen * cemento_ip_m3

        aditivo_rheo_sika115 = volumen * rheo_sika115_m3
        aditivo_basf_sika200 = volumen * basf_sika200_m3
        aditivo_delvo = volumen * delvo_m3
        aditivo_glenium_7950 = volumen * g7950_m3
        aditivo_glenium_7970 = volumen * g7970_m3
        aditivo_fibras = volumen * fibras_m3

        
        cemento_kg_viejo = cemento_he_kg + cemento_ip_kg
        aditivo_kg_viejo = (
            aditivo_rheo_sika115
            + aditivo_basf_sika200
            + aditivo_fibras
        )

        
        data = {
            "fecha": fecha,
            "volumen_m3": volumen,
            "diseno_mezcla": diseno_mezcla,
            "zona": destino,
            "wbs": wbs,
            "turno": turno,
            "arena_humedad_pct": float(humedad_arena or 0),
            "asentamiento_final_cm": float(asentamiento_final or 0),
            "temperatura_c": float(temperatura or 0),
            "arena_kg": arena_kg,
            "grava_kg": grava_kg,
            "agua_kg": agua_kg,
        }

        # Cementos
        if "cemento_he_kg" in cols_d:
            data["cemento_he_kg"] = cemento_he_kg
        if "cemento_ip_kg" in cols_d:
            data["cemento_ip_kg"] = cemento_ip_kg
        if "cemento_kg" in cols_d:
            data["cemento_kg"] = cemento_kg_viejo

        # Aditivos
        if "aditivo_rheo_sika115" in cols_d:
            data["aditivo_rheo_sika115"] = aditivo_rheo_sika115
        if "aditivo_basf_sika200" in cols_d:
            data["aditivo_basf_sika200"] = aditivo_basf_sika200
        if "aditivo_delvo" in cols_d:
            data["aditivo_delvo"] = aditivo_delvo
        if "aditivo_glenium_7950" in cols_d:
            data["aditivo_glenium_7950"] = aditivo_glenium_7950
        if "aditivo_glenium_7970" in cols_d:
            data["aditivo_glenium_7970"] = aditivo_glenium_7970
        if "aditivo_fibras" in cols_d:
            data["aditivo_fibras"] = aditivo_fibras
        if "aditivo_kg" in cols_d:
            data["aditivo_kg"] = aditivo_kg_viejo

        cols = list(data.keys())
        placeholders = ",".join(["?"] * len(cols))
        sql = f"INSERT INTO despachos ({','.join(cols)}) VALUES ({placeholders})"

        cur = conn.cursor()
        cur.execute(sql, tuple(data[c] for c in cols))
        conn.commit()
        return cur.lastrowid

    except Exception:
        return None
    finally:
        conn.close()


# =========================================================
# Historial 
# =========================================================
def obtener_historial_consumo(
    inicio: str,
    fin: str,
    diseno=None,
    zona=None,
    turno=None,
    wbs=None,
):
    """
    Retorna filas para Historial/Gráficas con llaves coherentes:
    - arena_kg, grava_kg, cemento_he_kg, cemento_ip_kg, agua_kg
    - aditivo_rheo_sika115, aditivo_basf_sika200, aditivo_delvo,
      aditivo_glenium_7950, aditivo_glenium_7970, aditivo_fibras

    Si la tabla despachos ya trae esas columnas, las usa directo.
    Si no, calcula usando JOIN con recetas.
    """
    conn = _connect()
    try:
        cols_d = _table_cols(conn, "despachos")
        cols_r = _table_cols(conn, "recetas")

        where = ["d.fecha BETWEEN ? AND ?"]
        params = [inicio, fin]

        if diseno and diseno != "Todos":
            where.append("d.diseno_mezcla = ?")
            params.append(diseno)
        if zona:
            where.append("d.zona LIKE ?")
            params.append(f"%{zona}%")
        if turno:
            where.append("d.turno = ?")
            params.append(turno)
        if wbs:
            where.append("d.wbs LIKE ?")
            params.append(f"%{wbs}%")

        
        has_new = all(
            c in cols_d
            for c in [
                "arena_kg",
                "grava_kg",
                "agua_kg",
                "cemento_he_kg",
                "cemento_ip_kg",
                "aditivo_rheo_sika115",
                "aditivo_basf_sika200",
                "aditivo_delvo",
                "aditivo_glenium_7950",
                "aditivo_glenium_7970",
                "aditivo_fibras",
            ]
        )

        cur = conn.cursor()

        if has_new:
            sql = f"""
                SELECT
                    d.id, d.fecha, d.diseno_mezcla, d.zona, d.wbs, d.turno, d.volumen_m3,
                    d.arena_humedad_pct, d.asentamiento_final_cm, d.temperatura_c,
                    d.arena_kg, d.grava_kg, d.agua_kg,
                    d.cemento_he_kg, d.cemento_ip_kg,
                    d.aditivo_rheo_sika115, d.aditivo_basf_sika200,
                    d.aditivo_delvo, d.aditivo_glenium_7950, d.aditivo_glenium_7970, d.aditivo_fibras
                FROM despachos d
                WHERE {" AND ".join(where)}
                ORDER BY d.fecha DESC, d.id DESC
            """
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

            out = []
            for row in rows:
                out.append({
                    "id": row["id"],
                    "fecha": row["fecha"],
                    "diseno_mezcla": row["diseno_mezcla"],
                    "zona": row["zona"],
                    "wbs": row["wbs"],
                    "turno": row["turno"],
                    "volumen_m3": float(row["volumen_m3"] or 0),

                    "arena_humedad_pct": float(row["arena_humedad_pct"] or 0),
                    "asentamiento_final_cm": float(row["asentamiento_final_cm"] or 0),
                    "temperatura_c": float(row["temperatura_c"] or 0),

                    "arena_kg": float(row["arena_kg"] or 0),
                    "grava_kg": float(row["grava_kg"] or 0),
                    "cemento_he_kg": float(row["cemento_he_kg"] or 0),
                    "cemento_ip_kg": float(row["cemento_ip_kg"] or 0),
                    "agua_kg": float(row["agua_kg"] or 0),

                    "aditivo_rheo_sika115": float(row["aditivo_rheo_sika115"] or 0),
                    "aditivo_basf_sika200": float(row["aditivo_basf_sika200"] or 0),
                    "aditivo_delvo": float(row["aditivo_delvo"] or 0),
                    "aditivo_glenium_7950": float(row["aditivo_glenium_7950"] or 0),
                    "aditivo_glenium_7970": float(row["aditivo_glenium_7970"] or 0),
                    "aditivo_fibras": float(row["aditivo_fibras"] or 0),
                })
            return out

        
        sql = f"""
            SELECT
                d.id, d.fecha, d.diseno_mezcla, d.zona, d.wbs, d.turno, d.volumen_m3,
                d.arena_humedad_pct, d.asentamiento_final_cm, d.temperatura_c,

                r.arena_kg AS r_arena_kg,
                r.grava_kg AS r_grava_kg,
                r.agua_kg  AS r_agua_kg,

                r.cemento_kg AS r_cemento_kg,
                r.cemento_he_kg AS r_cemento_he_kg,
                r.cemento_ip_kg AS r_cemento_ip_kg,

                r.aditivo_a AS r_aditivo_a,
                r.aditivo_b AS r_aditivo_b,
                r.aditivo_rheo_sika115 AS r_aditivo_rheo_sika115,
                r.aditivo_basf_sika200 AS r_aditivo_basf_sika200,

                r.delvo_l AS r_delvo_l,
                r.glenium_7950 AS r_glenium_7950,
                r.glenium_7970 AS r_glenium_7970,
                r.fibras_kg AS r_fibras_kg
            FROM despachos d
            LEFT JOIN recetas r ON r.codigo_diseno = d.diseno_mezcla
            WHERE {" AND ".join(where)}
            ORDER BY d.fecha DESC, d.id DESC
        """

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

        out = []
        for row in rows:
            v = float(row["volumen_m3"] or 0)

            r_arena = float(row["r_arena_kg"] or 0)
            r_grava = float(row["r_grava_kg"] or 0)
            r_agua = float(row["r_agua_kg"] or 0)

            # Cementos
            r_cem_he = float(row["r_cemento_he_kg"] or 0) if "cemento_he_kg" in cols_r else 0.0
            r_cem_ip = float(row["r_cemento_ip_kg"] or 0) if "cemento_ip_kg" in cols_r else 0.0
            if (r_cem_he == 0.0 and r_cem_ip == 0.0):
                r_cem_he = float(row["r_cemento_kg"] or 0)

            # Aditivos
            if "aditivo_rheo_sika115" in cols_r:
                r_a = float(row["r_aditivo_rheo_sika115"] or 0)
            else:
                r_a = float(row["r_aditivo_a"] or 0)

            if "aditivo_basf_sika200" in cols_r:
                r_b = float(row["r_aditivo_basf_sika200"] or 0)
            else:
                r_b = float(row["r_aditivo_b"] or 0)

            r_delvo = float(row["r_delvo_l"] or 0)
            r_g7950 = float(row["r_glenium_7950"] or 0)
            r_g7970 = float(row["r_glenium_7970"] or 0)
            r_fib = float(row["r_fibras_kg"] or 0)

            out.append({
                "id": row["id"],
                "fecha": row["fecha"],
                "diseno_mezcla": row["diseno_mezcla"],
                "zona": row["zona"],
                "wbs": row["wbs"],
                "turno": row["turno"],
                "volumen_m3": v,

                "arena_humedad_pct": float(row["arena_humedad_pct"] or 0),
                "asentamiento_final_cm": float(row["asentamiento_final_cm"] or 0),
                "temperatura_c": float(row["temperatura_c"] or 0),

                "arena_kg": v * r_arena,
                "grava_kg": v * r_grava,
                "cemento_he_kg": v * r_cem_he,
                "cemento_ip_kg": v * r_cem_ip,
                "agua_kg": v * r_agua,

                "aditivo_rheo_sika115": v * r_a,
                "aditivo_basf_sika200": v * r_b,
                "aditivo_delvo": v * r_delvo,
                "aditivo_glenium_7950": v * r_g7950,
                "aditivo_glenium_7970": v * r_g7970,
                "aditivo_fibras": v * r_fib,
            })

        return out

    finally:
        conn.close()


# =========================================================
# Resumen por rango 
# =========================================================
def cruce_consumo_por_rango(inicio, fin, diseno=None, zona=None, turno=None, wbs=None):
    """
    Suma consumo total estimado (entre inicio/fin) por material.
    Retorna dict con llaves coherentes con app.py (charts).
    """
    filas = obtener_historial_consumo(inicio, fin, diseno=diseno, zona=zona, turno=turno, wbs=wbs)

    tot = {
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
    }

    for f in filas:
        for k in tot.keys():
            try:
                tot[k] += float(f.get(k, 0) or 0)
            except Exception:
                pass

    for k in list(tot.keys()):
        tot[k] = round(tot[k], 6)

    return tot


# =========================================================
# Cruce consumo vs stock (materiales)
# =========================================================
def cruzar_consumo_vs_stock(resumen_consumo: dict):
    """
    Cruza el consumo total con stock en tabla 'materiales' (si existe el material).

    Retorna:
    - filas: lista de dicts con material, stock, consumo, saldo
    - no_mapeados: keys de resumen sin mapeo a material
    - no_encontrados: materiales mapeados pero no existen en tabla materiales
    """
    MAP = {
        "arena_kg": "Arena",
        "grava_kg": "Grava",
        "cemento_he_kg": "Cemento HE",
        "cemento_ip_kg": "Cemento IP",
        "agua_kg": "Agua",
        "aditivo_rheo_sika115": "RHEO 1000",
        "aditivo_basf_sika200": "BASF 719",
        "aditivo_delvo": "Delvo",
        "aditivo_glenium_7950": "MasterGlenium 7950",
        "aditivo_glenium_7970": "MasterGlenium 7970",
        "aditivo_fibras": "Sika PP 48 - BARCHIP",
    }

    conn = _connect()
    try:
        cur = conn.cursor()

        filas = []
        no_mapeados = []
        no_encontrados = []

        for k, consumo in (resumen_consumo or {}).items():
            if k not in MAP:
                no_mapeados.append(k)
                continue

            mat = MAP[k]

            
            cur.execute("SELECT stock_actual FROM materiales WHERE nombre = ?", (mat,))
            r = cur.fetchone()
            if not r:
                no_encontrados.append(mat)
                continue

            stock = float(r["stock_actual"] or 0)
            c = float(consumo or 0)
            filas.append({
                "key": k,
                "material": mat,
                "stock_actual": stock,
                "consumo_estimado": c,
                "saldo": round(stock - c, 6),
            })

        return filas, no_mapeados, no_encontrados
    finally:
        conn.close()
