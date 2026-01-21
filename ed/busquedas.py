# ed/busquedas.py
from utils.loaders import _connect, _parse_fecha_to_iso


def buscar_por_rango(inicio, fin):
    """
    Retorna:
      - resultados: lista de dicts con llaves esperadas por historial.js
      - bst_time: float (placeholder)
      - avl_time: float (placeholder)
    """
    ini = _parse_fecha_to_iso(inicio)
    fi = _parse_fecha_to_iso(fin)

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                id, fecha, diseno_mezcla, zona, wbs, turno, volumen_m3,
                arena_kg, grava_kg, cemento_he_kg, cemento_ip_kg, agua_kg,
                aditivo_a, aditivo_b, aditivo_delvo, aditivo_glenium_7950, aditivo_glenium_7970, aditivo_fibras,
                arena_humedad_pct, asentamiento_final_cm, temperatura_c
            FROM despachos
            WHERE fecha BETWEEN ? AND ?
            ORDER BY fecha DESC, id DESC
            """,
            (ini, fi),
        )

        out = []
        for r in cur.fetchall():
            out.append({
                "id": r["id"],
                "fecha": r["fecha"],
                "diseno": r["diseno_mezcla"],
                "zona": r["zona"],
                "wbs": r["wbs"],
                "turno": r["turno"],
                "volumen_m3": float(r["volumen_m3"] or 0),

                "est_arena_kg": float(r["arena_kg"] or 0),
                "est_grava_kg": float(r["grava_kg"] or 0),
                "est_cemento_he_kg": float(r["cemento_he_kg"] or 0),
                "est_cemento_ip_kg": float(r["cemento_ip_kg"] or 0),
                "est_agua_kg": float(r["agua_kg"] or 0),

                # En UI:
                "est_aditivo_rheo_sika115": float(r["aditivo_a"] or 0),
                "est_aditivo_basf_sika200": float(r["aditivo_b"] or 0),
                "est_aditivo_delvo": float(r["aditivo_delvo"] or 0),
                "est_aditivo_glenium_7950": float(r["aditivo_glenium_7950"] or 0),
                "est_aditivo_glenium_7970": float(r["aditivo_glenium_7970"] or 0),
                "est_aditivo_fibras": float(r["aditivo_fibras"] or 0),

                "humedad": float(r["arena_humedad_pct"] or 0),
                "asentamiento": float(r["asentamiento_final_cm"] or 0),
                "temperatura": float(r["temperatura_c"] or 0),
            })

        # placeholders (tu UI muestra chips, pero no vamos a romper nada)
        bst_time = 0.0
        avl_time = 0.0
        return out, bst_time, avl_time
    finally:
        conn.close()


def busqueda_diseno_destino(resultados, diseno=None, destino=None, turno=None, wbs=None):
    """
    Filtra en memoria sobre los resultados ya obtenidos.
    """
    data = resultados or []

    if diseno and diseno != "Todos":
        data = [x for x in data if str(x.get("diseno", "")).strip() == str(diseno).strip()]

    if destino:
        d = str(destino).strip().lower()
        data = [x for x in data if d in str(x.get("zona", "")).strip().lower()]

    if turno and turno != "Todos":
        data = [x for x in data if str(x.get("turno", "")).strip() == str(turno).strip()]

    if wbs:
        w = str(wbs).strip().lower()
        data = [x for x in data if w in str(x.get("wbs", "")).strip().lower()]

    return data
