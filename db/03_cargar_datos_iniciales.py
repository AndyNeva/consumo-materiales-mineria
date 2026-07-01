import pandas as pd
import sqlite3
import os
from utilidades import limpiar_numero

#Configuración
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")
EXCEL_PATH = os.path.join(BASE_DIR, "data", "raw", "Batch_Plant_Production_2025.xlsm")

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

def cargar_datos():
    """Migra datos históricos del Excel a la BD relacional"""
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("PRAGMA foreign_keys = ON;")
    cursor = conexion.cursor()

    # Obtener mapa de insumos para buscar por nombre
    cursor.execute("SELECT id_insumo, nombre_insumo FROM Insumos")
    mapa_insumos = {fila[1].lower(): fila[0] for fila in cursor.fetchall()}

    # Mapeo de columnas de insumos en Ingreso_Diario
    columnas_insumos_despacho = {
        "Arena (kg)": "Arena",
        "Grava (kg)": "Grava",
        "UCEM HE (kg)": "Cemento",
        "Agua (kg)": "Agua",
        "RHEO 1000 (kg)  Sika 115 (kg)": "RHEO 1000",
        "BASF 719 (kg)  Sika 200 (kg)": "BASF 719",
        "Delvo (litros)": "Delvo",
        "MasterGlenium 7950": "Glenium 7950",
        "MasterGlenium 7970": "Glenium 7970",
        "Sika PP 48 (kg)-BARCHIP": "Fibras",
    }

    # Mapeo de columnas de insumos en Recetas (Base de Datos )
    columnas_insumos_receta = {
        "CEMENTO": "Cemento",
        "Arena (kg)": "Arena",
        "Grava (kg)": "Grava",
        "Agua (kg)": "Agua",
        "RHEO 1000 (kg)  Sika 115 (kg)": "RHEO 1000",
        "BASF 719 (kg)  Sika 200 (kg)": "BASF 719",
        "Delvo (litros)": "Delvo",
        "MasterGlenium 7950": "Glenium 7950",
        "MasterGlenium 7970": "Glenium 7970",
        "Sika PP 48 (kg)-BARCHIP": "Fibras",
    }

    # ========== DESPACHOS (PRODUCCIÓN DIARIA) ==========
    print(" Leyendo hoja 'Ingreso_Diario' del Excel (puede demorar de 15 a 30 segundos)...")
    df_desp = pd.read_excel(EXCEL_PATH, sheet_name="Ingreso_Diario", header=0, engine='openpyxl')
    df_desp.columns = df_desp.columns.str.strip()

    total_filas = len(df_desp)
    print(f" [OK] Leídas {total_filas} filas. Cargando en Base de Datos...")

    for idx, fila in df_desp.iterrows():
        if idx > 0 and idx % 1000 == 0:
            print(f"   -> Procesadas {idx}/{total_filas} filas...")

        fecha = str(fila.get('FECHA')).split(' ')[0]
        if pd.isna(fila.get('FECHA')) or fecha in ['NaT', 'nan', '', '-']:
            continue

        diseno = str(fila.get('Diseño de la Mezcla','')).strip()
        zona = str(fila.get('Zona','')).strip()
        wbs = str(fila.get('WBS','')).strip()

        diseno_mezcla = obtener_o_crear_mezcla(cursor, diseno)
        id_zona = obtener_o_crear_zona(cursor, zona)
        id_cc = obtener_o_crear_cc(cursor, wbs)

        volumen = limpiar_numero(fila.get('Volumen (m3)'))

        cursor.execute("""
            INSERT INTO Produccion_Diaria (
                fecha, lote_numero, volumen_m3, diseno_mezcla, id_zona, id_cc,
                arena_humedad_pct, asentamiento_final_cm, temperatura_c, turno
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fecha,
            str(fila.get('Lote #','')),
            volumen,
            diseno_mezcla,
            id_zona,
            id_cc,
            limpiar_numero(fila.get('ARENA HUMEDAD (%)')),
            limpiar_numero(fila.get('Asentamiento Final (cm)')),
            limpiar_numero(fila.get('Temp. (º C)')),
            str(fila.get('Turno', fila.get('TURNO', '')))
        ))
        id_produccion = cursor.lastrowid

        # Insertar consumos en Produccion_Insumos
        for col_excel, nombre_insumo in columnas_insumos_despacho.items():
            cant = limpiar_numero(fila.get(col_excel))
            if cant > 0:
                id_insumo = mapa_insumos.get(nombre_insumo.lower())
                if id_insumo:
                    cursor.execute("""
                        INSERT INTO Produccion_Insumos (id_produccion, id_insumo, cantidad_real)
                        VALUES (?, ?, ?)
                    """, (id_produccion, id_insumo, cant))

    print(f" [OK] Producción Diaria cargada ({total_filas} registros procesados).")

    # ========== INVENTARIO ==========
    print("\n Leyendo hoja 'INGRESOS Y CONSUMO DE AGREGADOS' del Excel...")
    df_inv = pd.read_excel(EXCEL_PATH, sheet_name="INGRESOS Y CONSUMO DE AGREGADOS", header=1, engine='openpyxl')

    # Resolver IDs para Arena, Grava, Cemento
    id_arena = mapa_insumos.get("arena")
    id_grava = mapa_insumos.get("grava")
    id_cemento = mapa_insumos.get("cemento")

    total_inv = len(df_inv)
    print(f" [OK] Leídas {total_inv} filas de inventario. Cargando en Base de Datos...")

    for idx, fila in df_inv.iterrows():
        if idx > 0 and idx % 1000 == 0:
            print(f"   -> Procesadas {idx}/{total_inv} filas de inventario...")

        fecha = str(fila.iloc[0]).split(' ')[0]
        if pd.isna(fila.iloc[0]) or fecha in ['NaT', 'nan', '']:
            continue

        prov = "Desconocido"
        try:
            if str(fila.iloc[10]).strip() not in ['-', 'nan', '']:
                prov = "Armijos"
            elif str(fila.iloc[11]).strip() not in ['-', 'nan', '']:
                prov = "Crusermine"
            elif str(fila.iloc[12]).strip() not in ['-', 'nan', '']:
                prov = "Quiringue"
        except:
            pass

        movs = [
            (1, id_arena, 'INGRESO'), (2, id_grava, 'INGRESO'), (3, id_cemento, 'INGRESO'),
            (4, id_arena, 'EGRESO'),  (5, id_grava, 'EGRESO'),  (6, id_cemento, 'EGRESO')
        ]

        for col, id_insumo, tipo in movs:
            if not id_insumo:
                continue
            cant = limpiar_numero(fila.iloc[col])
            if cant > 0:
                cursor.execute(
                    "INSERT INTO movimientos (usuario_id, id_insumo, cantidad, fecha, tipo, proveedor) VALUES (?,?,?,?,?,?)",
                    (1, id_insumo, cant, fecha, tipo, prov)
                )

    print(f" [OK] Inventario cargado ({total_inv} registros procesados).")

    # ========== RECETAS ==========
    print("\n Leyendo hoja 'Base de Datos ' (Recetas)...")
    df_mst = pd.read_excel(EXCEL_PATH, sheet_name="Base de Datos ", header=1, engine='openpyxl')
    df_mst.columns = df_mst.columns.astype(str).str.strip()

    col_diseno = next((c for c in df_mst.columns if "DISEÑO" in c.upper()), None)

    total_rec = len(df_mst)
    print(f" [OK] Leídas {total_rec} filas de recetas. Cargando en Base de Datos...")

    if col_diseno:
        for _, fila in df_mst.iterrows():
            cod = str(fila[col_diseno]).strip()
            if cod in ['', 'nan', '-']:
                continue

            diseno_mezcla = obtener_o_crear_mezcla(cursor, cod)

            for col_excel, nombre_insumo in columnas_insumos_receta.items():
                cant = limpiar_numero(fila.get(col_excel))
                if cant > 0:
                    id_insumo = mapa_insumos.get(nombre_insumo.lower())
                    if id_insumo:
                        cursor.execute("""
                            INSERT OR REPLACE INTO Receta_Detalle (diseno_mezcla, id_insumo, cantidad_requerida)
                            VALUES (?, ?, ?)
                        """, (diseno_mezcla, id_insumo, cant))

    conexion.commit()
    conexion.close()
    print("Migración de datos completada.")

if __name__ == "__main__":
    cargar_datos()
