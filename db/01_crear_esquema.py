import sqlite3
import os

# Control de seguridad para evitar borrar la BD por error

PERMITIR_RECREAR_DB = True  

# Configuración de rutas

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

def crear_esquema():
    """Crea el esquema completo de la base de datos"""
    
    # Eliminar BD anterior si está permitido
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

    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            rol TEXT
        )
    ''')

    # Tabla de insumos (Materiales)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Insumos (
            id_insumo INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_insumo TEXT UNIQUE NOT NULL,
            unidad TEXT,
            stock_minimo REAL DEFAULT 0,
            stock_maximo REAL DEFAULT 0,
            stock_actual REAL DEFAULT 0
        )
    ''')

    # Tabla de movimientos de inventario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            id_insumo INTEGER,
            cantidad REAL,
            fecha TEXT,
            tipo TEXT,
            proveedor TEXT,
            detalle TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (id_insumo) REFERENCES Insumos(id_insumo)
        )
    ''')

    # Tabla de Zonas (Catálogo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Zonas (
            id_zona INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_zona TEXT UNIQUE NOT NULL
        )
    ''')

    # Tabla de Centros de Costo (Catálogo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Centros_Costo (
            id_cc INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_cc TEXT UNIQUE NOT NULL
        )
    ''')

    # Tabla de Diseños de Mezcla (Recetas cabecera)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Disenos_Mezcla (
            diseno_mezcla TEXT PRIMARY KEY
        )
    ''')

    # Tabla de Receta Detalle (Ingredientes de las recetas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Receta_Detalle (
            id_receta INTEGER PRIMARY KEY AUTOINCREMENT,
            diseno_mezcla TEXT,
            id_insumo INTEGER,
            cantidad_requerida REAL,
            UNIQUE(diseno_mezcla, id_insumo),
            FOREIGN KEY (diseno_mezcla) REFERENCES Disenos_Mezcla(diseno_mezcla) ON DELETE CASCADE,
            FOREIGN KEY (id_insumo) REFERENCES Insumos(id_insumo)
        )
    ''')

    # Tabla de Producción Diaria (Cabecera de despachos/lotes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Produccion_Diaria (
            id_produccion INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            lote_numero TEXT,
            volumen_m3 REAL,
            diseno_mezcla TEXT,
            id_zona INTEGER,
            id_cc INTEGER,
            arena_humedad_pct REAL,
            asentamiento_final_cm REAL,
            temperatura_c REAL,
            turno TEXT,
            FOREIGN KEY (diseno_mezcla) REFERENCES Disenos_Mezcla(diseno_mezcla),
            FOREIGN KEY (id_zona) REFERENCES Zonas(id_zona),
            FOREIGN KEY (id_cc) REFERENCES Centros_Costo(id_cc)
        )
    ''')

    # Tabla de Producción Insumos (Consumos reales de cada despacho)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Produccion_Insumos (
            id_produccion INTEGER,
            id_insumo INTEGER,
            cantidad_real REAL,
            PRIMARY KEY (id_produccion, id_insumo),
            FOREIGN KEY (id_produccion) REFERENCES Produccion_Diaria(id_produccion) ON DELETE CASCADE,
            FOREIGN KEY (id_insumo) REFERENCES Insumos(id_insumo)
        )
    ''')

    # Tabla de demanda diaria
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_demand (
            date TEXT PRIMARY KEY,
            volume_m3 REAL NOT NULL
        )
    ''')

    # tabla q persiste los intentos fallidos de login y el bloqueo temporal.
    # se guarda en bd (no en memoria) para q el bloqueo aguante reinicios del
    # servidor; asi un ataque de fuerza bruta no se reinicia con el proceso.
    # la clave es usuario+ip; bloqueado_hasta es un timestamp unix.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intentos_login (
            clave TEXT PRIMARY KEY,
            intentos INTEGER NOT NULL DEFAULT 0,
            bloqueado_hasta REAL NOT NULL DEFAULT 0
        )
    ''')

    conexion.commit()
    conexion.close()
    print("Esquema relacional creado correctamente.")


if __name__ == "__main__":
    crear_esquema()
