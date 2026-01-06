from flask import current_app
import sqlite3
from pathlib import Path
import os

# Ruta base del proyecto (carpeta proyecto-consumo-materiales)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ruta absoluta a la base de datos
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")


def obtener_conexion_flask():
    """
    Obtiene una conexión a la base de datos dentro del contexto de Flask.
    """
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # permite dict(row)
    return conn

def obtener_conexion_autonoma():
    """
    Obtiene una conexión a la base de datos fuera del contexto de Flask
    (útil para ED, ML o scripts independientes).
    """
    db_path = Path(__file__).parent.parent / "db" / "gestion_materiales.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # permite dict(row)
    return conn

def cargar_datos_tabla(tabla: str):
    """
    Carga todos los registros de una tabla específica como lista de diccionarios.
    Parámetros:
        tabla (str): Nombre de la tabla en la base de datos (ej. 'consumo', 'materiales', 'usuarios').
    Devuelve:
        list[dict]: Lista con todos los registros de la tabla.
    """

    tablas_permitidas = {'despachos', 'movimientos', 'recetas'}
    # Valida que la tabla solicitada esté en la lista permitida
    if tabla not in tablas_permitidas:
        raise ValueError(f"Tabla '{tabla}' no permitida. Use: {tablas_permitidas}")

    try:
        # Intenta usar el contexto de Flask
        conn = obtener_conexion_flask()
    except RuntimeError:
        # Fuera de Flask usa conexión autónoma
        conn = obtener_conexion_autonoma()

    cursor = conn.cursor()
    # Ejecuta la consulta SQL para obtener TODOS los registros de la tabla
    cursor.execute(f"SELECT * FROM {tabla}")
    datos = cursor.fetchall()
    conn.close()

    # Convertir sqlite3.Row a dict estándar
    return [dict(fila) for fila in datos]