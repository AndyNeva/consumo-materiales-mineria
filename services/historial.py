from __future__ import annotations
from typing import Any, Dict, List, Optional
from utils.db import conectar, columnas_tabla, float_seguro, RUTA_BD


def obtener_historial_consumo(
    inicio: str,
    fin: str,
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
    ruta_bd: str = RUTA_BD,
) -> List[Dict[str, Any]]:
    """
    Obtiene historial de despachos con filtros opcionales usando SQL puro.

    Args:
        inicio (str): Fecha de inicio en formato YYYY-MM-DD.
        fin (str): Fecha de fin en formato YYYY-MM-DD.
        diseno (str): Código de diseño de mezcla (opcional).
        zona (str): Zona o destino (opcional).
        turno (str): Turno de trabajo (opcional).
        wbs (str): Código WBS (opcional).
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        List[Dict]: Lista de despachos que cumplen los filtros.
    """
    with conectar(ruta_bd) as conexion:
        columnas = columnas_tabla(conexion, "despachos")

        condiciones = ["fecha >= ? AND fecha <= ?"]
        parametros: List[Any] = [inicio, fin]

        if diseno:
            condiciones.append("diseno_mezcla = ?")
            parametros.append(diseno)
        if zona:
            condiciones.append("zona LIKE ?")
            parametros.append(f"%{zona}%")
        if turno:
            condiciones.append("turno = ?")
            parametros.append(turno)
        if wbs:
            condiciones.append("wbs LIKE ?")
            parametros.append(f"%{wbs}%")

        columnas_seleccion = [
            "id", "fecha", "diseno_mezcla", "zona", "turno", "wbs", "volumen_m3",
            "arena_kg", "grava_kg", "cemento_kg", "agua_kg",
            "aditivo_rheo_sika115", "aditivo_basf_sika200", "aditivo_delvo",
            "aditivo_glenium_7950", "aditivo_glenium_7970", "aditivo_fibras",
            "arena_humedad_pct", "asentamiento_final_cm", "temperatura_c",
        ]
        columnas_finales = [c for c in columnas_seleccion if c in columnas]

        sql = f"""
            SELECT {", ".join(columnas_finales)}
            FROM despachos
            WHERE {" AND ".join(condiciones)}
            ORDER BY fecha ASC, id ASC
        """
        cursor = conexion.execute(sql, parametros)
        return [dict(fila) for fila in cursor.fetchall()]


def cruce_consumo_por_rango(
    inicio: str,
    fin: str,
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
    ruta_bd: str = RUTA_BD,
) -> Dict[str, Any]:
    """
    Suma total de consumos de materiales en un rango de fechas.

    Args:
        inicio (str): Fecha de inicio en formato YYYY-MM-DD.
        fin (str): Fecha de fin en formato YYYY-MM-DD.
        diseno (str): Filtro por diseño de mezcla (opcional).
        zona (str): Filtro por zona (opcional).
        turno (str): Filtro por turno (opcional).
        wbs (str): Filtro por WBS (opcional).
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        Dict: Totales de consumo por material en el rango.
    """
    filas = obtener_historial_consumo(inicio, fin, diseno, zona, turno, wbs, ruta_bd=ruta_bd)

    totales: Dict[str, Any] = {
        "registros": len(filas),
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

    for fila in filas:
        for campo in totales:
            if campo == "registros":
                continue
            totales[campo] += float_seguro(fila.get(campo))

    return totales