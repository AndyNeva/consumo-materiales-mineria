import sqlite3
import os

# CONTROL DE SEGURIDAD
# Evita borrar la base de datos por error

PERMITIR_RECREAR_DB = True  # Cambiar a True SOLO en migración inicial o rrecrear db

# CONFIGURACIÓN DE RUTAS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

# CREACIÓN DEL ESQUEMA DE LA BASE DE DATOS

def crear_esquema():
    # Si existe una base anterior, se elimina (si está permitido)
    if os.path.exists(DB_PATH):
        if PERMITIR_RECREAR_DB:
            try:
                os.remove(DB_PATH)
                print(" DB anterior eliminada (modo migración).")
            except PermissionError:
                print("Cierra programas que estén usando la DB.")
        else:
            print(" Recreación de la base BLOQUEADA.")
            print("  Cambie PERMITIR_RECREAR_DB = True para permitirlo.")
            return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            rol TEXT
        )
    ''')

    # Tabla de materiales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materiales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            unidad TEXT
        )
    ''')

# --- AGREGAR COLUMNAS DE INVENTARIO A MATERIALES ---
# Estas columnas forman parte del inventario
# Si ya existen, SQLite lanzará error y lo ignoramos

    for columna, definicion in [
        ("stock_minimo", "REAL DEFAULT 0"),
        ("stock_maximo", "REAL DEFAULT 0"),
        ("stock_actual", "REAL DEFAULT 0")
    ]:
        try:
            cursor.execute(f"ALTER TABLE materiales ADD COLUMN {columna} {definicion}")
            print(f"✅ Columna {columna} agregada a materiales.")
        except sqlite3.OperationalError:
            # La columna ya existe
            pass
    # Tabla de movimientos de inventario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            material_id INTEGER,
            cantidad REAL,
            fecha TEXT,
            tipo TEXT,
            proveedor TEXT,
            detalle TEXT
        )
    ''')

    # Tabla de despachos (producción)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS despachos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            fuente_cemento TEXT,
            diseno_mezcla TEXT,
            lote TEXT,
            zona TEXT,
            wbs TEXT,
            volumen_m3 REAL,
            turno TEXT,
            arena_humedad_pct REAL,
            asentamiento_final_cm REAL,
            temperatura_c REAL,
            arena_kg REAL,
            grava_kg REAL,
            cemento_kg REAL,
            agua_kg REAL,
            aditivo_rheo_sika115 REAL,
            aditivo_basf_sika200 REAL,
            aditivo_delvo REAL,
            aditivo_glenium_7950 REAL,
            aditivo_glenium_7970 REAL,
            aditivo_fibras REAL
        )
    ''')
    #tabla de demanda
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_demand (
            date TEXT PRIMARY KEY,
            volume_m3 REAL NOT NULL
        )
    ''')

    # Tabla de recetas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_diseno TEXT UNIQUE,
            cemento_kg REAL,
            arena_kg REAL,
            grava_kg REAL,
            agua_kg REAL,
            aditivo_a REAL DEFAULT 0,
            aditivo_b REAL DEFAULT 0,
            aditivo_delvo REAL DEFAULT 0,
            aditivo_glenium_7950 REAL DEFAULT 0,
            aditivo_glenium_7970 REAL DEFAULT 0,
            aditivo_fibras REAL DEFAULT 0
        )
    ''')

    # Catálogos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS centros_costos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zonas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Esquema creado correctamente.")

# --------------------------------------------------
# EJECUCIÓN DIRECTA
# --------------------------------------------------
if __name__ == "__main__":
    crear_esquema()
