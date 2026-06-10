from __future__ import annotations
from typing import Any, Dict, Optional
from utils.db import conectar, columnas_tabla, float_seguro, valor_fila, RUTA_BD

def _receta_por_diseno(conexion, diseno: str):
    """
    Busca una receta por código de diseño.

    Args:
        conexion: Conexión activa a la BD.
        diseno (str): Código del diseño de mezcla.

    Returns:
        sqlite3.Row | None: Fila de la receta o None si no existe.
    """
    cursor = conexion.execute(
        "SELECT * FROM recetas WHERE codigo_diseno = ? LIMIT 1", (diseno,)
    )
    return cursor.fetchone()

def _calcular_consumos_estimados(receta, volumen_m3: float) -> Dict[str, float]:
    """
    Calcula consumos de materiales según receta y volumen.

    Args:
        receta: Fila de la tabla recetas.
        volumen_m3 (float): Volumen producido en metros cúbicos.

    Returns:
        Dict[str, float]: Consumo estimado por material.
    """
    return {
        "arena_kg":            float_seguro(valor_fila(receta, "arena_kg", 0.0)) * volumen_m3,
        "grava_kg":            float_seguro(valor_fila(receta, "grava_kg", 0.0)) * volumen_m3,
        "agua_kg":             float_seguro(valor_fila(receta, "agua_kg", 0.0)) * volumen_m3,
        "cemento_kg":          float_seguro(valor_fila(receta, "cemento_kg", 0.0)) * volumen_m3,
        "aditivo_rheo_sika115": float_seguro(valor_fila(receta, "aditivo_a", 0.0)) * volumen_m3,
        "aditivo_basf_sika200": float_seguro(valor_fila(receta, "aditivo_b", 0.0)) * volumen_m3,
        "aditivo_delvo":        float_seguro(valor_fila(receta, "aditivo_delvo", 0.0)) * volumen_m3,
        "aditivo_glenium_7950": float_seguro(valor_fila(receta, "aditivo_glenium_7950", 0.0)) * volumen_m3,
        "aditivo_glenium_7970": float_seguro(valor_fila(receta, "aditivo_glenium_7970", 0.0)) * volumen_m3,
        "aditivo_fibras":       float_seguro(valor_fila(receta, "aditivo_fibras", 0.0)) * volumen_m3,
    }

def insertar_despacho(
    fecha: str,
    volumen: float,
    diseno_mezcla: str,
    wbs: str,
    destino: str,
    turno: str,
    humedad_arena: Optional[float] = None,
    asentamiento_final: Optional[float] = None,
    temperatura: Optional[float] = None,
    ruta_bd: str = RUTA_BD,
) -> Optional[int]:
    """
    Inserta un nuevo despacho y descuenta stock de materiales.

    Args:
        fecha (str): Fecha del despacho en formato YYYY-MM-DD.
        volumen (float): Volumen producido en m3.
        diseno_mezcla (str): Código del diseño de mezcla.
        wbs (str): Código WBS del proyecto.
        destino (str): Zona o destino de la producción.
        turno (str): Turno de trabajo.
        humedad_arena (float): Porcentaje de humedad de la arena.
        asentamiento_final (float): Asentamiento final en cm.
        temperatura (float): Temperatura de la mezcla en grados C.
        ruta_bd (str): Ruta a la base de datos.

    Returns:
        int | None: ID del despacho insertado o None si falló.
    """
    try:
        volumen_m3 = float(volumen)
    except Exception:
        return None

    if volumen_m3 <= 0 or not diseno_mezcla:
        return None

    with conectar(ruta_bd) as conexion:
        receta = _receta_por_diseno(conexion, diseno_mezcla)
        if receta is None:
            return None

        estimados = _calcular_consumos_estimados(receta, volumen_m3)

        datos: Dict[str, Any] = {
            "fecha": fecha,
            "volumen_m3": volumen_m3,
            "diseno_mezcla": diseno_mezcla,
            "zona": destino,
            "wbs": wbs,
            "turno": turno,
            "arena_humedad_pct": humedad_arena,
            "asentamiento_final_cm": asentamiento_final,
            "temperatura_c": temperatura,
            **estimados,
        }

        columnas = columnas_tabla(conexion, "despachos")
        datos = {k: v for k, v in datos.items() if k in columnas}

        marcadores = ", ".join(["?"] * len(datos))
        columnas_sql = ", ".join(datos.keys())
        sql = f"INSERT INTO despachos ({columnas_sql}) VALUES ({marcadores})"

        cursor = conexion.execute(sql, tuple(datos.values()))
        conexion.commit()
        id_insertado = int(cursor.lastrowid)

        mapeo_consumo_material = {
            "arena_kg": "Arena",
            "grava_kg": "Grava",
            "cemento_kg": "Cemento",
            "agua_kg": "Agua",
            "aditivo_rheo_sika115": "RHEO 1000",
            "aditivo_basf_sika200": "BASF 719",
            "aditivo_delvo": "Delvo",
            "aditivo_glenium_7950": "Glenium 7950",
            "aditivo_glenium_7970": "Glenium 7970",
            "aditivo_fibras": "Fibras",
        }

        for campo, nombre_material in mapeo_consumo_material.items():
            cantidad = estimados.get(campo, 0.0)
            if cantidad == 0:
                continue
            cursor2 = conexion.execute(
                "SELECT stock_actual FROM materiales WHERE LOWER(nombre)=LOWER(?) LIMIT 1",
                (nombre_material,)
            )
            fila = cursor2.fetchone()
            if fila is not None:
                nuevo_stock = float(fila["stock_actual"] or 0) - cantidad
                conexion.execute(
                    "UPDATE materiales SET stock_actual = ? WHERE LOWER(nombre)=LOWER(?)",
                    (nuevo_stock, nombre_material)
                )

        conexion.commit()
        return id_insertado