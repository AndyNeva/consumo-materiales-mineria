from __future__ import annotations
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

# Ruta por defecto de la base de datos
RUTA_BD = "db/gestion_materiales.db"

# ===== FUNCIONES AUXILIARES =====

def _conectar(ruta_bd: str = RUTA_BD) -> sqlite3.Connection:
    """Crea conexión a BD con soporte de diccionarios"""
    conexion = sqlite3.connect(ruta_bd)
    conexion.row_factory = sqlite3.Row
    return conexion

def _columnas_tabla(conexion: sqlite3.Connection, tabla: str) -> List[str]:
    """Obtiene lista de columnas de una tabla"""
    cursor = conexion.execute(f"PRAGMA table_info({tabla})")
    return [fila["name"] for fila in cursor.fetchall()]

def _float_seguro(valor: Any, predeterminado: float = 0.0) -> float:
    """Convierte valor a float de forma segura"""
    if valor is None:
        return predeterminado
    try:
        return float(valor)
    except Exception:
        return predeterminado

def _valor_fila(fila: Any, clave: str, predeterminado: Any = None) -> Any:
    """Acceso seguro a valores de fila (sqlite3.Row o dict)"""
    if fila is None:
        return predeterminado
    try:
        return fila[clave]
    except Exception:
        try:
            return fila.get(clave, predeterminado)
        except Exception:
            return predeterminado

def _receta_por_diseno(conexion: sqlite3.Connection, diseno: str) -> Optional[sqlite3.Row]:
    """Busca receta por código de diseño"""
    cursor = conexion.execute("SELECT * FROM recetas WHERE codigo_diseno = ? LIMIT 1", (diseno,))
    return cursor.fetchone()

def _material_por_nombre(conexion: sqlite3.Connection, nombre: str) -> Optional[sqlite3.Row]:
    """Busca material por nombre (case-insensitive)"""
    cursor = conexion.execute("SELECT * FROM materiales WHERE LOWER(nombre)=LOWER(?) LIMIT 1", (nombre,))
    return cursor.fetchone()

def _calcular_consumos_estimados(receta: sqlite3.Row, volumen_m3: float) -> Dict[str, float]:
    """Calcula consumos de materiales según receta y volumen"""
    arena = _float_seguro(_valor_fila(receta, "arena_kg", 0.0)) * volumen_m3
    grava = _float_seguro(_valor_fila(receta, "grava_kg", 0.0)) * volumen_m3
    agua = _float_seguro(_valor_fila(receta, "agua_kg", 0.0)) * volumen_m3
    cemento = _float_seguro(_valor_fila(receta, "cemento_kg", 0.0)) * volumen_m3

    rheo = _float_seguro(_valor_fila(receta, "aditivo_a", 0.0)) * volumen_m3
    basf = _float_seguro(_valor_fila(receta, "aditivo_b", 0.0)) * volumen_m3
    delvo = _float_seguro(_valor_fila(receta, "aditivo_delvo", 0.0)) * volumen_m3
    gl7950 = _float_seguro(_valor_fila(receta, "aditivo_glenium_7950", 0.0)) * volumen_m3
    gl7970 = _float_seguro(_valor_fila(receta, "aditivo_glenium_7970", 0.0)) * volumen_m3
    fibras = _float_seguro(_valor_fila(receta, "aditivo_fibras", 0.0)) * volumen_m3

    return {
        "arena_kg": arena,
        "grava_kg": grava,
        "agua_kg": agua,
        "cemento_kg": cemento,
        "aditivo_rheo_sika115": rheo,
        "aditivo_basf_sika200": basf,
        "aditivo_delvo": delvo,
        "aditivo_glenium_7950": gl7950,
        "aditivo_glenium_7970": gl7970,
        "aditivo_fibras": fibras,
    }

# ===== FUNCIONES DE CARGA =====

def cargar_datos_tabla(tabla: str, ruta_bd: str = RUTA_BD) -> List[Dict[str, Any]]:
    """Carga todos los registros de una tabla"""
    with _conectar(ruta_bd) as conexion:
        cursor = conexion.cursor()
        cursor.execute(f"SELECT * FROM {tabla}")
        return [dict(fila) for fila in cursor.fetchall()]

def convertir_formato_historial(registros: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convierte registros de BD al formato del frontend"""
    salida = []
    for reg in registros:
        salida.append({
            "id": reg.get("id"),
            "fecha": reg.get("fecha"),
            "diseno": reg.get("diseno_mezcla"),
            "zona": reg.get("zona"),
            "wbs": reg.get("wbs"),
            "turno": reg.get("turno"),
            "volumen_m3": float(reg.get("volumen_m3") or 0),
            "arena_kg": float(reg.get("arena_kg") or 0),
            "grava_kg": float(reg.get("grava_kg") or 0),
            "cemento_kg": float(reg.get("cemento_kg") or 0),
            "agua_kg": float(reg.get("agua_kg") or 0),
            "aditivo_rheo_sika115": float(reg.get("aditivo_rheo_sika115") or 0),
            "aditivo_basf_sika200": float(reg.get("aditivo_basf_sika200") or 0),
            "aditivo_delvo": float(reg.get("aditivo_delvo") or 0),
            "aditivo_glenium_7950": float(reg.get("aditivo_glenium_7950") or 0),
            "aditivo_glenium_7970": float(reg.get("aditivo_glenium_7970") or 0),
            "aditivo_fibras": float(reg.get("aditivo_fibras") or 0),
            "arena_humedad_pct": float(reg.get("arena_humedad_pct") or 0),
            "asentamiento_final_cm": float(reg.get("asentamiento_final_cm") or 0),
            "temperatura_c": float(reg.get("temperatura_c") or 0),
        })
    return salida


# ===== DASHBOARD =====

def consumo_diario(fecha: Optional[str] = None, ruta_bd: str = RUTA_BD) -> float:
    """Obtiene volumen total consumido en una fecha"""
    if not fecha:
        fecha = date.today().isoformat()

    with _conectar(ruta_bd) as conexion:
        cursor = conexion.execute(
            "SELECT COALESCE(SUM(volumen_m3),0) AS total FROM despachos WHERE fecha = ?",
            (fecha,),
        )
        return float(cursor.fetchone()["total"])

def registros_ultima_semana(ruta_bd: str = RUTA_BD) -> Tuple[List[Dict[str, Any]], int]:
    """Obtiene despachos de últimos 7 días"""
    with _conectar(ruta_bd) as conexion:
        cursor = conexion.execute(
            """
            SELECT fecha, diseno_mezcla, zona, wbs, volumen_m3
            FROM despachos
            WHERE fecha >= date('now','-6 day')
            ORDER BY fecha DESC, id DESC
            """
        )
        filas = [dict(fila) for fila in cursor.fetchall()]

        cursor2 = conexion.execute(
            """
            SELECT COUNT(*) AS n
            FROM despachos
            WHERE fecha >= date('now','-6 day')
            """
        )
        cantidad = int(cursor2.fetchone()["n"])
        return filas, cantidad

# ===== INSERTAR DESPACHO =====

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
    """Inserta nuevo despacho y descuenta stock de materiales"""
    
    try:
        volumen_m3 = float(volumen)
    except Exception:
        return None

    if volumen_m3 <= 0 or not diseno_mezcla:
        return None

    with _conectar(ruta_bd) as conexion:
        # Buscar la receta correspondiente al diseño
        receta = _receta_por_diseno(conexion, diseno_mezcla)
        if receta is None:
            return None

        # Calcular el consumo estimado de materiales
        estimados = _calcular_consumos_estimados(receta, volumen_m3)

        # Preparar los datos para insertar en la tabla despachos
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

        # Filtrar solo las columnas que existen en la tabla
        columnas = _columnas_tabla(conexion, "despachos")
        datos = {k: v for k, v in datos.items() if k in columnas}

        marcadores = ", ".join(["?"] * len(datos))
        columnas_sql = ", ".join(datos.keys())
        sql = f"INSERT INTO despachos ({columnas_sql}) VALUES ({marcadores})"

        cursor = conexion.execute(sql, tuple(datos.values()))
        conexion.commit()
        id_insertado = int(cursor.lastrowid)

        # Descontar el stock de cada material usado en el despacho
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
            
            cursor2 = conexion.execute("SELECT stock_actual FROM materiales WHERE LOWER(nombre)=LOWER(?) LIMIT 1", (nombre_material,))
            fila = cursor2.fetchone()
            if fila is not None:
                stock_actual = float(fila["stock_actual"] or 0)
                nuevo_stock = stock_actual - cantidad
                conexion.execute("UPDATE materiales SET stock_actual = ? WHERE LOWER(nombre)=LOWER(?)", (nuevo_stock, nombre_material))
        
        conexion.commit()
        return id_insertado

# ===== HISTORIAL Y CONSULTAS =====

def obtener_historial_consumo(
    inicio: str,
    fin: str,
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
    ruta_bd: str = RUTA_BD,
) -> List[Dict[str, Any]]:
    """Obtiene historial de consumo con filtros opcionales"""
    
    with _conectar(ruta_bd) as conexion:
        columnas = _columnas_tabla(conexion, "despachos")

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

        salida: List[Dict[str, Any]] = []
        for fila in cursor.fetchall():
            salida.append(dict(fila))
        return salida

def cruce_consumo_por_rango(
    inicio: str,
    fin: str,
    diseno: Optional[str] = None,
    zona: Optional[str] = None,
    turno: Optional[str] = None,
    wbs: Optional[str] = None,
    ruta_bd: str = RUTA_BD,
) -> Dict[str, Any]:
    """Suma total de consumos en un rango de fechas"""
    
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
        totales["volumen_m3"] += _float_seguro(fila.get("volumen_m3"))
        totales["arena_kg"] += _float_seguro(fila.get("arena_kg"))
        totales["grava_kg"] += _float_seguro(fila.get("grava_kg"))
        totales["agua_kg"] += _float_seguro(fila.get("agua_kg"))
        totales["cemento_kg"] += _float_seguro(fila.get("cemento_kg"))
        totales["aditivo_rheo_sika115"] += _float_seguro(fila.get("aditivo_rheo_sika115"))
        totales["aditivo_basf_sika200"] += _float_seguro(fila.get("aditivo_basf_sika200"))
        totales["aditivo_delvo"] += _float_seguro(fila.get("aditivo_delvo"))
        totales["aditivo_glenium_7950"] += _float_seguro(fila.get("aditivo_glenium_7950"))
        totales["aditivo_glenium_7970"] += _float_seguro(fila.get("aditivo_glenium_7970"))
        totales["aditivo_fibras"] += _float_seguro(fila.get("aditivo_fibras"))

    return totales

# ===== CRUCE CONSUMO VS STOCK =====

def cruzar_consumo_vs_stock(
    resumen: Dict[str, Any],
    ruta_bd: str = RUTA_BD
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Compara consumo estimado contra stock disponible"""
    
    # Mapeo: (campo_consumo, nombre_material, unidad)
    mapa = [
        ("arena_kg", "Arena", "kg"),
        ("grava_kg", "Grava", "kg"),
        ("cemento_kg", "Cemento", "kg"),
        ("agua_kg", "Agua", "kg"),
        ("aditivo_rheo_sika115", "RHEO 1000", "kg"),
        ("aditivo_basf_sika200", "BASF 719", "kg"),
        ("aditivo_delvo", "Delvo", "l"),
        ("aditivo_glenium_7950", "Glenium 7950", "l"),
        ("aditivo_glenium_7970", "Glenium 7970", "l"),
        ("aditivo_fibras", "Fibras", "kg"),
    ]

    no_mapeados: List[str] = []
    no_encontrados: List[str] = []
    salida: List[Dict[str, Any]] = []

    with _conectar(ruta_bd) as conexion:
        columnas_materiales = _columnas_tabla(conexion, "materiales")

        columna_stock = "stock_actual"
        columna_minimo = "stock_minimo"

        for campo, nombre, unidad in mapa:
            consumo = _float_seguro(resumen.get(campo))

            material = _material_por_nombre(conexion, nombre)
            if not material:
                if consumo > 0:
                    no_encontrados.append(nombre)
                stock = 0.0
                minimo = 0.0
            else:
                stock = _float_seguro(_valor_fila(material, columna_stock, 0.0)) if columna_stock else 0.0
                minimo = _float_seguro(_valor_fila(material, columna_minimo, 0.0)) if columna_minimo else 0.0

            saldo = stock - consumo
            bajo_minimo = (stock < minimo) if minimo > 0 else False

            # Determinar estado
            estado = "OK"
            if saldo < 0:
                estado = "Deficit"
            elif bajo_minimo:
                estado = "Bajo minimo"

            salida.append({
                "material": nombre,
                "unidad": unidad,
                "stock_actual": stock,
                "minimo": minimo,
                "consumo_estimado": consumo,
                "saldo": saldo,
                "bajo_minimo": bajo_minimo,
                "estado": estado,
            })

    # Detectar campos no mapeados con consumo
    campos_mapeados = {x[0] for x in mapa}
    for clave, valor in (resumen or {}).items():
        if clave in ("registros", "volumen_m3"):
            continue
        if (clave.endswith("_kg") or clave.startswith("aditivo_")) and clave not in campos_mapeados and _float_seguro(valor) != 0:
            no_mapeados.append(clave)

    return salida, no_mapeados, no_encontrados
