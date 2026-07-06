from __future__ import annotations
from typing import Any, Dict, Optional
from utils.db import conectar, float_seguro, valor_fila, RUTA_BD


def _float_flexible(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    return float(valor)

def _receta_por_diseno(conexion, diseno: str):
def _receta_por_diseno(conexion, diseno: str) -> Optional[Dict[str, Any]]:
    """
    Busca una receta por código de diseño y la retorna en el formato plano legacy
    para mantener compatibilidad.
    """
    cursor = conexion.execute(
        "SELECT diseno_mezcla FROM Disenos_Mezcla WHERE diseno_mezcla = ? LIMIT 1",
        (diseno,)
    )
    mezcla = cursor.fetchone()
    if not mezcla:
        return None

    diseno_mezcla = mezcla["diseno_mezcla"]
    cursor_ing = conexion.execute("""
        SELECT rd.cantidad_requerida, i.nombre_insumo
        FROM Receta_Detalle rd
        JOIN Insumos i ON rd.id_insumo = i.id_insumo
        WHERE rd.diseno_mezcla = ?
    """, (diseno_mezcla,))
    
    ingredientes = cursor_ing.fetchall()
    
    mapeo_insumo_a_columna = {
        "cemento": "cemento_kg",
        "arena": "arena_kg",
        "grava": "grava_kg",
        "agua": "agua_kg",
        "rheo 1000": "aditivo_a",
        "basf 719": "aditivo_b",
        "delvo": "aditivo_delvo",
        "glenium 7950": "aditivo_glenium_7950",
        "glenium 7970": "aditivo_glenium_7970",
        "fibras": "aditivo_fibras",
    }
    
    receta_plana = {
        "id": diseno_mezcla,
        "codigo_diseno": diseno_mezcla,
        "cemento_kg": 0.0,
        "arena_kg": 0.0,
        "grava_kg": 0.0,
        "agua_kg": 0.0,
        "aditivo_a": 0.0,
        "aditivo_b": 0.0,
        "aditivo_delvo": 0.0,
        "aditivo_glenium_7950": 0.0,
        "aditivo_glenium_7970": 0.0,
        "aditivo_fibras": 0.0
    }
    
    for ing in ingredientes:
        nombre = str(ing["nombre_insumo"]).lower()
        col = mapeo_insumo_a_columna.get(nombre)
        if col:
            receta_plana[col] = float(ing["cantidad_requerida"] or 0)
            
    return receta_plana

def _calcular_consumos_estimados(receta, volumen_m3: float) -> Dict[str, float]:
    """
    Calcula consumos de materiales según receta y volumen.
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

def obtener_o_crear_zona(cursor, nombre_zona):
    nombre = str(nombre_zona).strip()
    if not nombre or nombre in ['nan', '-', '', 'None']:
        return None
    cursor.execute("SELECT id_zona FROM Zonas WHERE nombre_zona = ?", (nombre,))
    fila = cursor.fetchone()
    if fila:
        return fila[0]
    cursor.execute("INSERT INTO Zonas (nombre_zona) VALUES (?)", (nombre,))
    return cursor.lastrowid

def obtener_o_crear_cc(cursor, codigo_cc):
    codigo = str(codigo_cc).strip()
    if not codigo or codigo in ['nan', '-', '', 'None']:
        return None
    cursor.execute("SELECT id_cc FROM Centros_Costo WHERE codigo_cc = ?", (codigo,))
    fila = cursor.fetchone()
    if fila:
        return fila[0]
    cursor.execute("INSERT INTO Centros_Costo (codigo_cc) VALUES (?)", (codigo,))
    return cursor.lastrowid

def obtener_o_crear_mezcla(cursor, diseno_mezcla):
    diseno = str(diseno_mezcla).strip()
    if not diseno or diseno in ['nan', '-', '', 'None']:
        return None
    cursor.execute("INSERT OR IGNORE INTO Disenos_Mezcla (diseno_mezcla) VALUES (?)", (diseno,))
    return diseno

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
    Inserta un nuevo despacho (Produccion_Diaria) y descuenta stock de Insumos.
    """
    try:
        volumen_m3 = _float_flexible(volumen)
    except Exception:
        return None

    if volumen_m3 is None or volumen_m3 <= 0 or not diseno_mezcla:
        return None

    humedad_arena = _float_flexible(humedad_arena)
    asentamiento_final = _float_flexible(asentamiento_final)
    temperatura = _float_flexible(temperatura)

    with conectar(ruta_bd) as conexion:
        # Habilitar soporte de llaves foráneas
        conexion.execute("PRAGMA foreign_keys = ON;")
        cursor = conexion.cursor()

        receta = _receta_por_diseno(conexion, diseno_mezcla)
        if receta is None:
            return None

        estimados = _calcular_consumos_estimados(receta, volumen_m3)

        diseno_mezcla_pk = obtener_o_crear_mezcla(cursor, diseno_mezcla)
        id_zona = obtener_o_crear_zona(cursor, destino)
        id_cc = obtener_o_crear_cc(cursor, wbs)

        cursor.execute("""
            INSERT INTO Produccion_Diaria (
                fecha, lote_numero, volumen_m3, diseno_mezcla, id_zona, id_cc,
                arena_humedad_pct, asentamiento_final_cm, temperatura_c, turno
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fecha,
            "", # lote_numero vacío al registrar por app
            volumen_m3,
            diseno_mezcla_pk,
            id_zona,
            id_cc,
            humedad_arena,
            asentamiento_final,
            temperatura,
            turno
        ))
        id_produccion = int(cursor.lastrowid)

        # Mapear de campos estimados a nombres de insumos en BD
        mapeo_consumo_insumo = {
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

        # Obtener mapa de nombres a ids de insumos
        cursor.execute("SELECT id_insumo, nombre_insumo FROM Insumos")
        mapa_insumos = {fila["nombre_insumo"].lower(): fila["id_insumo"] for fila in cursor.fetchall()}

        for campo, nombre_insumo in mapeo_consumo_insumo.items():
            cantidad = estimados.get(campo, 0.0)
            if cantidad <= 0:
                continue

            id_insumo = mapa_insumos.get(nombre_insumo.lower())
            if not id_insumo:
                continue

            # Insertar en Produccion_Insumos
            cursor.execute("""
                INSERT INTO Produccion_Insumos (id_produccion, id_insumo, cantidad_real)
                VALUES (?, ?, ?)
            """, (id_produccion, id_insumo, cantidad))

            # Descontar stock_actual en Insumos
            cursor.execute(
                "SELECT stock_actual FROM Insumos WHERE id_insumo = ? LIMIT 1",
                (id_insumo,)
            )
            fila = cursor.fetchone()
            if fila is not None:
                nuevo_stock = float(fila["stock_actual"] or 0) - cantidad
                cursor.execute(
                    "UPDATE Insumos SET stock_actual = ? WHERE id_insumo = ?",
                    (nuevo_stock, id_insumo)
                )

        conexion.commit()
        return id_produccion