from flask import current_app
import sqlite3
from pathlib import Path
from datetime import date
from utils.helpers import ultimos_7_dias

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

def consumo_diario():
    try:
        datos = cargar_datos_tabla('despachos')
        hoy = date.today().isoformat()
        consumo = 0
        
        for entrada in datos:
            if entrada['fecha'] == hoy:
                volumen = entrada.get('volumen_m3', 0)
                if isinstance(volumen, (int, float)):
                    consumo += volumen
        
        return consumo
    except Exception as e:
        print(f"Error al calcular consumo diario: {e}")
        return 0

def registros_ultima_semana():
    try:
        fechas = ultimos_7_dias()
        datos = cargar_datos_tabla('despachos')
        datos_finales = []

        for entrada in datos:
            if entrada.get('fecha') in fechas:
                # Filtrar solo los campos que necesitas
                registro_filtrado = {
                    'fecha': entrada.get('fecha', ''),
                    'diseno_mezcla': entrada.get('diseno_mezcla', ''),
                    'zona': entrada.get('zona', ''),
                    'wbs': entrada.get('wbs', ''),
                    'volumen_m3': entrada.get('volumen_m3', 0)
                }
                datos_finales.append(registro_filtrado)
        
        total_registros = len(datos_finales)
        return datos_finales, total_registros
    except Exception as e:
        print(f"Error al obtener registros de la última semana: {e}")
        return [], 0

def insertar_despacho(fecha, volumen, diseno_mezcla, wbs, destino, turno, humedad_arena, asentamiento_final, temperatura):
    """
    Inserta un nuevo registro en la tabla 'despachos'.

        fecha (str): Fecha en formato 'YYYY-MM-DD'.
        volumen (float): Volumen producido.
        diseno_mezcla (str): Diseño de mezcla.
        wbs (str): Código WBS.
        destino (str): Destino de la producción.
        humedad_arena (float): Humedad de la arena.
        asentamiento_final (float): Asentamiento final.
        temperatura (float): Temperatura de la mezcla.
    """
    # Validar parámetros requeridos
    if not fecha or not isinstance(fecha, str):
        print("Error: Fecha inválida o vacía")
        return None
    
    if not diseno_mezcla or not isinstance(diseno_mezcla, str):
        print("Error: Diseño de mezcla inválido o vacío")
        return None
    
    if not wbs or not isinstance(wbs, str):
        print("Error: WBS inválido o vacío")
        return None
    
    if not destino or not isinstance(destino, str):
        print("Error: Destino inválido o vacío")
        return None
    if not turno or not isinstance(turno, str):
        print("Error: Turno inválido o vacío")
    
    # Validar formato de fecha (YYYY-MM-DD)
    try:
        from datetime import datetime
        datetime.strptime(fecha, '%Y-%m-%d')
    except ValueError:
        print(f"Error: Formato de fecha inválido. Use 'YYYY-MM-DD'. Recibido: {fecha}")
        return None
    
    # Validar valores numéricos
    try:
        volumen = float(volumen)
        humedad_arena = float(humedad_arena)
        asentamiento_final = float(asentamiento_final)
        temperatura = float(temperatura)
    except (ValueError, TypeError):
        print("Error: Uno o más valores numéricos son inválidos")
        return None
    
    # Validar rangos razonables
    if volumen <= 0:
        print(f"Error: El volumen debe ser positivo. Recibido: {volumen}")
        return None
    
    if not (0 <= humedad_arena <= 100):
        print(f"Error: La humedad debe estar entre 0 y 100%. Recibido: {humedad_arena}")
        return None
    
    if asentamiento_final < 0:
        print(f"Error: El asentamiento no puede ser negativo. Recibido: {asentamiento_final}")
        return None
    
    if not (-10 <= temperatura <= 60):
        print(f"Error: Temperatura fuera de rango razonable (-10 a 60°C). Recibido: {temperatura}")
        return None
    
    # Fuente cemento
    fuente_cemento = "DIS_LI744"

    try:
        # Conectar a la base de datos
        conn = obtener_conexion_autonoma()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM recetas WHERE diseno_mezcla = ?", (diseno_mezcla,))
        receta = cursor.fetchone()

         # Validar que existe la receta
        if not receta:
            print(f"Error: No se encontró la receta para {diseno_mezcla}")
            conn.close()
            return None

        campos_receta = ["cemento_kg", "arena_kg", "grava_kg", "agua_kg", "aditivo_a", "aditivo_b", "aditivo_delvo", "aditivo_glenium_7950", "aditivo_glenium_7970", "aditivo_fibra"]
        valores_receta = [receta[campo] for campo in campos_receta]

        # Preparar la consulta SQL
        query = f"""
        INSERT INTO despachos (
            fecha, fuente_cemento, volumen_m3, diseno_mezcla, wbs, zona,
            arena_humedad_pct, asentamiento_final_cm, temperatura_c,{", ".join(campos_receta)}
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, {', '.join(['?'] * len(campos_receta))})
        """

        # Ejecutar la consulta con los parámetros
        cursor.execute(query, (
            fecha,
            fuente_cemento,
            volumen,
            diseno_mezcla,
            wbs,
            destino,
            humedad_arena,
            asentamiento_final,
            temperatura,
            *valores_receta
        ))

        # Obtener el ID del registro insertado
        despacho_id = cursor.lastrowid

        # Confirmar los cambios
        conn.commit()

        # Cerrar la conexión
        conn.close()

        return despacho_id

    except sqlite3.Error as e:
        print(f"Error al agregar nueva entrada: {e}")
        return None

def insertar_material(material, stock, unidad, minimo, usuario_id):
    # Validar parámetros requeridos
    if not material or not isinstance(material, str):
        print("Error: Nombre de material inválido o vacío")
        return None
    
    if not unidad or not isinstance(unidad, str):
        print("Error: Unidad inválida o vacía")
        return None
    
    # Validar valores numéricos
    try:
        stock = float(stock)
        minimo = float(minimo)
    except (ValueError, TypeError):
        print("Error: Stock o mínimo deben ser valores numéricos")
        return None
    
    # Validar rangos
    if stock < 0:
        print(f"Error: El stock no puede ser negativo. Recibido: {stock}")
        return None
    
    if minimo < 0:
        print(f"Error: El mínimo no puede ser negativo. Recibido: {minimo}")
        return None
    
    try:
        conn = obtener_conexion_autonoma()
        cursor = conn.cursor()
        
        # Verificar si el material ya existe
        cursor.execute("SELECT id FROM materiales WHERE nombre = ?", (material,))
        if cursor.fetchone():
            print(f"Error: El material '{material}' ya existe en la base de datos")
            conn.close()
            return None

        query_materiales = """
            INSERT INTO materiales (
                nombre, unidad, minimo
            ) VALUES (?, ?, ?)
            """
        
        cursor.execute(query_materiales, (material, unidad, minimo))

        material_id = cursor.lastrowid
        # Consultar como ingresar
        fecha = date.today()
        tipo = "INGRESO"
        # Definir si va o no
        proveedor = "Desconocido"

        query_movimientos = """
            INSERT INTO movimientos (
                usuario_id, material_id, cantidad, fecha, tipo, proveedor
            ) VALUES (?, ?, ?, ?, ?, ?)
            """
        
        cursor.execute(query_movimientos, (usuario_id, material_id, stock, fecha, tipo, proveedor))

        # Confirmar los cambios
        conn.commit()

        # Cerrar la conexión
        conn.close()

        return material_id
    except sqlite3.Error as e:
        print(f"Error al insertar material: {e}")
        return None
