from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Tuple
from utils.db import conectar, RUTA_BD


def consumo_diario(fecha: str = None, ruta_bd: str = RUTA_BD) -> float:
    """
    Obtiene el volumen total producido en una fecha.
    """
    if not fecha:
        fecha = date.today().isoformat()

    with conectar(ruta_bd) as conexion:
        cursor = conexion.execute(
            "SELECT COALESCE(SUM(volumen_m3), 0) AS total FROM Produccion_Diaria WHERE fecha = ?",
            (fecha,),
        )
        return float(cursor.fetchone()["total"])


def registros_ultima_semana(ruta_bd: str = RUTA_BD) -> Tuple[List[Dict[str, Any]], int]:
    """
    Obtiene los despachos de los últimos 7 días.
    """
    with conectar(ruta_bd) as conexion:
        cursor = conexion.execute(
            """
            SELECT 
                pd.fecha, 
                m.diseno_mezcla, 
                z.nombre_zona AS zona, 
                cc.codigo_cc AS wbs, 
                pd.volumen_m3
            FROM Produccion_Diaria pd
            LEFT JOIN Disenos_Mezcla m ON pd.diseno_mezcla = m.diseno_mezcla
            LEFT JOIN Zonas z ON pd.id_zona = z.id_zona
            LEFT JOIN Centros_Costo cc ON pd.id_cc = cc.id_cc
            WHERE pd.fecha >= date('now', '-6 day')
            ORDER BY pd.fecha DESC, pd.id_produccion DESC
            """
        )
        filas = [dict(fila) for fila in cursor.fetchall()]

        cursor2 = conexion.execute(
            """
            SELECT COUNT(*) AS n
            FROM Produccion_Diaria
            WHERE fecha >= date('now', '-6 day')
            """
        )
        cantidad = int(cursor2.fetchone()["n"])
        return filas, cantidad