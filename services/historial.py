from __future__ import annotations
from typing import Any, Dict, List, Optional
from utils.db import conectar, float_seguro, RUTA_BD


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
    Pivota los consumos reales para retornar la estructura plana legacy.
    """
    with conectar(ruta_bd) as conexion:
        condiciones = ["pd.fecha >= ? AND pd.fecha <= ?"]
        parametros: List[Any] = [inicio, fin]

        if diseno:
            condiciones.append("m.diseno_mezcla = ?")
            parametros.append(diseno)
        if zona:
            condiciones.append("z.nombre_zona LIKE ?")
            parametros.append(f"%{zona}%")
        if turno:
            condiciones.append("pd.turno = ?")
            parametros.append(turno)
        if wbs:
            condiciones.append("cc.codigo_cc LIKE ?")
            parametros.append(f"%{wbs}%")

        sql = f"""
            SELECT 
                pd.id_produccion AS id,
                pd.fecha,
                m.diseno_mezcla,
                z.nombre_zona AS zona,
                pd.turno,
                cc.codigo_cc AS wbs,
                pd.volumen_m3,
                pd.arena_humedad_pct,
                pd.asentamiento_final_cm,
                pd.temperatura_c
            FROM Produccion_Diaria pd
            LEFT JOIN Disenos_Mezcla m ON pd.diseno_mezcla = m.diseno_mezcla
            LEFT JOIN Zonas z ON pd.id_zona = z.id_zona
            LEFT JOIN Centros_Costo cc ON pd.id_cc = cc.id_cc
            WHERE {" AND ".join(condiciones)}
            ORDER BY pd.fecha ASC, pd.id_produccion ASC
        """
        cursor = conexion.execute(sql, parametros)
        filas = [dict(fila) for fila in cursor.fetchall()]

        if not filas:
            return []

        # Mapa para pivotar nombres de insumos a columnas legacy
        mapeo_insumo_a_columna = {
            "arena": "arena_kg",
            "grava": "grava_kg",
            "cemento": "cemento_kg",
            "agua": "agua_kg",
            "rheo 1000": "aditivo_rheo_sika115",
            "basf 719": "aditivo_basf_sika200",
            "delvo": "aditivo_delvo",
            "glenium 7950": "aditivo_glenium_7950",
            "glenium 7970": "aditivo_glenium_7970",
            "fibras": "aditivo_fibras",
        }

        for fila in filas:
            for col in mapeo_insumo_a_columna.values():
                fila[col] = 0.0

            cursor_c = conexion.execute("""
                SELECT pi.cantidad_real, i.nombre_insumo
                FROM Produccion_Insumos pi
                JOIN Insumos i ON pi.id_insumo = i.id_insumo
                WHERE pi.id_produccion = ?
            """, (fila["id"],))

            for cons in cursor_c.fetchall():
                nombre = str(cons["nombre_insumo"]).lower()
                col = mapeo_insumo_a_columna.get(nombre)
                if col:
                    fila[col] = float(cons["cantidad_real"] or 0.0)

        return filas


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