from __future__ import annotations
import sqlite3
import os
from typing import Any, List
from dotenv import load_dotenv

load_dotenv()

RUTA_BD = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "gestion_materiales.db"))

_TABLAS_PERMITIDAS = frozenset({
    "despachos", "materiales", "usuarios",
    "recetas", "movimientos", "centros_costos", "zonas",
    "intentos_login"
})

def conectar(ruta_bd: str = RUTA_BD) -> sqlite3.Connection:
    """
    Crea y retorna una conexión a la base de datos.

    Args:
        ruta_bd (str): Ruta al archivo de la base de datos.

    Returns:
        sqlite3.Connection: Conexión con row_factory para retornar diccionarios.
    """
    conexion = sqlite3.connect(ruta_bd)
    conexion.row_factory = sqlite3.Row
    return conexion

def columnas_tabla(conexion: sqlite3.Connection, tabla: str) -> List[str]:
    """
    Obtiene los nombres de columnas de una tabla.

    Args:
        conexion: Conexión activa a la BD.
        tabla (str): Nombre de la tabla.

    Returns:
        List[str]: Lista de nombres de columnas.
    """
    if tabla not in _TABLAS_PERMITIDAS:
        raise ValueError(f"Tabla '{tabla}' no permitida.")
    cursor = conexion.execute(f"PRAGMA table_info({tabla})")
    return [fila["name"] for fila in cursor.fetchall()]

def float_seguro(valor: Any, predeterminado: float = 0.0) -> float:
    """
    Convierte un valor a float de forma segura.

    Args:
        valor: Valor a convertir.
        predeterminado (float): Valor si la conversión falla.

    Returns:
        float: Valor convertido o predeterminado.
    """
    if valor is None:
        return predeterminado
    try:
        return float(valor)
    except Exception:
        return predeterminado

def valor_fila(fila: Any, clave: str, predeterminado: Any = None) -> Any:
    """
    Acceso seguro a valores de fila sqlite3.Row o dict.

    Args:
        fila: Fila de resultado de la BD.
        clave (str): Nombre del campo.
        predeterminado: Valor si no existe la clave.

    Returns:
        Any: Valor del campo o predeterminado.
    """
    if fila is None:
        return predeterminado
    try:
        return fila[clave]
    except Exception:
        try:
            return fila.get(clave, predeterminado)
        except Exception:
            return predeterminado