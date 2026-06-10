from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Tuple
from utils.db import conectar, RUTA_BD


def consumo_diario(fecha: str = None, ruta_bd: str = RUTA_BD) -> float:
    """
    Obtiene el volumen total producido en una fecha.

    Args:
        fecha (str): Fecha en formato YYYY-MM-DD. Si no se envía usa hoy.
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        float: Volumen total en m3.
    """
    if not fecha:
        fecha = date.today().isoformat()

    with conectar(ruta_bd) as conexion:
        cursor = conexion.execute(
            "SELECT COALESCE(SUM(volumen_m3), 0) AS total FROM despachos WHERE fecha = ?",
            (fecha,),
        )
        return float(cursor.fetchone()["total"])


def registros_ultima_semana(ruta_bd: str = RUTA_BD) -> Tuple[List[Dict[str, Any]], int]:
    """
    Obtiene los despachos de los últimos 7 días.

    Args:
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        Tuple: (lista de despachos, cantidad total).
    """
    with conectar(ruta_bd) as conexion:
        cursor = conexion.execute(
            """
            SELECT fecha, diseno_mezcla, zona, wbs, volumen_m3
            FROM despachos
            WHERE fecha >= date('now', '-6 day')
            ORDER BY fecha DESC, id DESC
            """
        )
        filas = [dict(fila) for fila in cursor.fetchall()]

        cursor2 = conexion.execute(
            """
            SELECT COUNT(*) AS n
            FROM despachos
            WHERE fecha >= date('now', '-6 day')
            """
        )
        cantidad = int(cursor2.fetchone()["n"])
        return filas, cantidad