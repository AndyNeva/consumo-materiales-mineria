from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from utils.db import conectar, float_seguro, valor_fila, RUTA_BD


def _material_por_nombre(conexion, nombre: str):
    """
    Busca un material por nombre de forma case-insensitive.

    Args:
        conexion: Conexión activa a la BD.
        nombre (str): Nombre del material.

    Returns:
        sqlite3.Row | None: Fila del material o None si no existe.
    """
    cursor = conexion.execute(
        "SELECT id_insumo AS id, nombre_insumo AS nombre, unidad, stock_actual, stock_minimo, stock_maximo "
        "FROM Insumos WHERE LOWER(nombre_insumo)=LOWER(?) LIMIT 1",
        (nombre,)
    )
    return cursor.fetchone()


def obtener_materiales(ruta_bd: str = RUTA_BD) -> List[Dict[str, Any]]:
    """
    Obtiene todos los materiales del inventario.

    Args:
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        List[Dict]: Lista de materiales con su stock actual.
    """
    with conectar(ruta_bd) as conexion:
        cursor = conexion.execute("""
            SELECT id_insumo AS id, nombre_insumo AS nombre, unidad, stock_actual, stock_minimo, stock_maximo
            FROM Insumos
            ORDER BY nombre_insumo
        """)
        return [dict(fila) for fila in cursor.fetchall()]


def actualizar_material(
    material_id: int,
    stock_actual: Optional[float] = None,
    stock_minimo: Optional[float] = None,
    stock_maximo: Optional[float] = None,
    ruta_bd: str = RUTA_BD,
) -> bool:
    """
    Actualiza stock de un material existente.

    Args:
        material_id (int): ID del material a actualizar.
        stock_actual (float): Nuevo stock actual (opcional).
        stock_minimo (float): Nuevo stock mínimo (opcional).
        stock_maximo (float): Nuevo stock máximo (opcional).
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        bool: True si se actualizó, False si no se encontró el material.
    """
    actualizaciones = []
    parametros = []

    if stock_actual is not None:
        actualizaciones.append("stock_actual = ?")
        parametros.append(float(stock_actual))

    if stock_minimo is not None:
        actualizaciones.append("stock_minimo = ?")
        parametros.append(float(stock_minimo))

    if stock_maximo is not None:
        actualizaciones.append("stock_maximo = ?")
        parametros.append(float(stock_maximo))

    if not actualizaciones:
        return False

    parametros.append(material_id)
    sql = f"UPDATE Insumos SET {', '.join(actualizaciones)} WHERE id_insumo = ?"

    with conectar(ruta_bd) as conexion:
        cursor = conexion.execute(sql, parametros)
        conexion.commit()
        return cursor.rowcount > 0


def agregar_material(
    nombre: str,
    unidad: str,
    stock_actual: float,
    stock_minimo: float,
    stock_maximo: float,
    ruta_bd: str = RUTA_BD,
) -> Optional[int]:
    """
    Inserta un nuevo material en el inventario.

    Args:
        nombre (str): Nombre del material.
        unidad (str): Unidad de medida (kg, l, m3, etc.).
        stock_actual (float): Cantidad disponible actualmente.
        stock_minimo (float): Umbral mínimo de alerta.
        stock_maximo (float): Capacidad máxima de almacenamiento.
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        int | None: ID del material insertado o None si falló.
    """
    nombre = (nombre or "").strip()
    unidad = (unidad or "").strip()
    if not nombre or not unidad:
        return None

    with conectar(ruta_bd) as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO Insumos (nombre_insumo, unidad, stock_actual, stock_minimo, stock_maximo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nombre, unidad, float(stock_actual), float(stock_minimo), float(stock_maximo))
        )
        conexion.commit()
        return int(cursor.lastrowid)


def eliminar_material(
    material_id: int,
    ruta_bd: str = RUTA_BD,
) -> Tuple[bool, str]:
    """
    Elimina un material si no tiene despachos asociados.

    Args:
        material_id (int): ID del material a eliminar.
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        Tuple[bool, str]: (éxito, mensaje descriptivo).
    """
    with conectar(ruta_bd) as conexion:
        # Verificar que el material existe
        cursor = conexion.execute(
            "SELECT nombre_insumo FROM Insumos WHERE id_insumo = ? LIMIT 1",
            (material_id,)
        )
        material = cursor.fetchone()
        if not material:
            return False, "Material no encontrado"

        conexion.execute(
            "DELETE FROM Insumos WHERE id_insumo = ?",
            (material_id,)
        )
        conexion.commit()
        return True, f"Material eliminado correctamente"


def cruzar_consumo_vs_stock(
    resumen: Dict[str, Any],
    ruta_bd: str = RUTA_BD,
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Compara consumo estimado contra stock disponible.

    Args:
        resumen (Dict): Totales de consumo por campo.
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        Tuple: (filas de cruce, campos no mapeados, materiales no encontrados).
    """
    mapa = [
        ("arena_kg",            "Arena",        "kg"),
        ("grava_kg",            "Grava",        "kg"),
        ("cemento_kg",          "Cemento",      "kg"),
        ("agua_kg",             "Agua",         "kg"),
        ("aditivo_rheo_sika115","RHEO 1000",    "kg"),
        ("aditivo_basf_sika200","BASF 719",     "kg"),
        ("aditivo_delvo",       "Delvo",        "l"),
        ("aditivo_glenium_7950","Glenium 7950", "l"),
        ("aditivo_glenium_7970","Glenium 7970", "l"),
        ("aditivo_fibras",      "Fibras",       "kg"),
    ]

    no_mapeados: List[str] = []
    no_encontrados: List[str] = []
    salida: List[Dict[str, Any]] = []

    with conectar(ruta_bd) as conexion:
        for campo, nombre, unidad in mapa:
            consumo = float_seguro(resumen.get(campo))
            material = _material_por_nombre(conexion, nombre)

            if not material:
                if consumo > 0:
                    no_encontrados.append(nombre)
                stock = 0.0
                minimo = 0.0
            else:
                stock  = float_seguro(valor_fila(material, "stock_actual", 0.0))
                minimo = float_seguro(valor_fila(material, "stock_minimo", 0.0))
                maximo = float_seguro(valor_fila(material, "stock_maximo", 0.0))

            if not material:
                maximo = 0.0

            saldo = stock - consumo
            deficit_sugerido = abs(saldo) if saldo < 0 else 0.0
            bajo_minimo = (stock < minimo) if minimo > 0 else False

            estado = "OK"
            if saldo < 0:
                estado = "Deficit"
            elif bajo_minimo:
                estado = "Bajo minimo"

            salida.append({
                "material":         nombre,
                "unidad":           unidad,
                "stock_actual":     stock,
                "minimo":           minimo,
                "maximo":           maximo,
                "consumo_estimado": consumo,
                "saldo":            saldo,
                "deficit_sugerido": deficit_sugerido,
                "bajo_minimo":      bajo_minimo,
                "estado":           estado,
            })

    campos_mapeados = {x[0] for x in mapa}
    for clave, valor in (resumen or {}).items():
        if clave in ("registros", "volumen_m3"):
            continue
        if (clave.endswith("_kg") or clave.startswith("aditivo_")) \
                and clave not in campos_mapeados \
                and float_seguro(valor) != 0:
            no_mapeados.append(clave)

    return salida, no_mapeados, no_encontrados