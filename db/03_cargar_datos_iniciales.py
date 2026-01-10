import pandas as pd
import sqlite3
import os
from utilidades import limpiar_numero

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")
EXCEL_PATH = os.path.join(BASE_DIR, "data", "raw", "Batch_Plant_Production_2025.xlsm")

# --------------------------------------------------
# MAPEO EXACTO DE COLUMNAS DEL EXCEL
# --------------------------------------------------
COLUMNAS_RECETAS = {
    "cemento_kg": "CEMENTO",
    "arena_kg": "Arena (kg)",
    "grava_kg": "Grava (kg)",
    "agua_kg": "Agua (kg)",
    "aditivo_a": "RHEO 1000 (kg)  Sika 115 (kg)",
    "aditivo_b": "BASF 719 (kg)  Sika 200 (kg)",
    "aditivo_delvo": "Delvo (litros)",
    "aditivo_glenium_7950": "MasterGlenium 7950",
    "aditivo_glenium_7970": "MasterGlenium 7970",
    "aditivo_fibras": "Sika PP 48 (kg)-BARCHIP"
}

# --------------------------------------------------
# MIGRACIÓN DE DATOS HISTÓRICOS
# --------------------------------------------------
def cargar_datos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ========== A. DESPACHOS ==========
    print(" Cargando Despachos...")
    df_desp = pd.read_excel(EXCEL_PATH, sheet_name="Ingreso_Diario", header=0, engine='openpyxl')
    df_desp.columns = df_desp.columns.str.strip()

    for _, row in df_desp.iterrows():
        fecha = str(row.get('FECHA')).split(' ')[0]
        if pd.isna(row.get('FECHA')) or fecha in ['NaT', 'nan', '', '-']:
            continue

        cursor.execute("""
            INSERT INTO despachos (
                fecha, fuente_cemento, diseno_mezcla, lote, zona, wbs, volumen_m3, turno,
                arena_humedad_pct, asentamiento_final_cm, temperatura_c,
                arena_kg, grava_kg, cemento_kg, agua_kg,
                aditivo_rheo_sika115, aditivo_basf_sika200, aditivo_delvo,
                aditivo_glenium_7950, aditivo_glenium_7970, aditivo_fibras
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            fecha,
            str(row.get('Fuente de cemento','')),
            str(row.get('Diseño de la Mezcla','')),
            str(row.get('Lote #','')),
            str(row.get('Zona','')),
            str(row.get('WBS','')),
            limpiar_numero(row.get('Volumen (m3)')),
            str(row.get('Turno', row.get('TURNO', ''))),
            limpiar_numero(row.get('ARENA HUMEDAD (%)')),
            limpiar_numero(row.get('Asentamiento Final (cm)')),
            limpiar_numero(row.get('Temp. (º C)')),
            limpiar_numero(row.get('Arena (kg)')),
            limpiar_numero(row.get('Grava (kg)')),
            limpiar_numero(row.get('UCEM HE (kg)')),
            limpiar_numero(row.get('Agua (kg)')),
            limpiar_numero(row.get('RHEO 1000 (kg)  Sika 115 (kg)')),
            limpiar_numero(row.get('BASF 719 (kg)  Sika 200 (kg)')),
            limpiar_numero(row.get('Delvo (litros)')),
            limpiar_numero(row.get('MasterGlenium 7950')),
            limpiar_numero(row.get('MasterGlenium 7970')),
            limpiar_numero(row.get('Sika PP 48 (kg)-BARCHIP'))
        ))

    # ========== B. INVENTARIO ==========
    print("Cargando Inventario...")
    df_inv = pd.read_excel(EXCEL_PATH, sheet_name="INGRESOS Y CONSUMO DE AGREGADOS", header=1, engine='openpyxl')

    for _, row in df_inv.iterrows():
        fecha = str(row.iloc[0]).split(' ')[0]
        if pd.isna(row.iloc[0]) or fecha in ['NaT', 'nan', '']:
            continue

        prov = "Desconocido"
        try:
            if str(row.iloc[10]).strip() not in ['-', 'nan', '']:
                prov = "Armijos"
            elif str(row.iloc[11]).strip() not in ['-', 'nan', '']:
                prov = "Crusermine"
            elif str(row.iloc[12]).strip() not in ['-', 'nan', '']:
                prov = "Quiringue"
        except:
            pass

        movs = [
            (1,1,'INGRESO'), (2,2,'INGRESO'), (3,3,'INGRESO'),
            (4,1,'EGRESO'),  (5,2,'EGRESO'),  (6,3,'EGRESO')
        ]

        for col, mat, tipo in movs:
            cant = limpiar_numero(row.iloc[col])
            if cant > 0:
                cursor.execute(
                    "INSERT INTO movimientos (usuario_id, material_id, cantidad, fecha, tipo, proveedor) VALUES (?,?,?,?,?,?)",
                    (1, mat, cant, fecha, tipo, prov)
                )

    # ========== C. RECETAS ==========
    print("Cargando Recetas...")
    df_mst = pd.read_excel(EXCEL_PATH, sheet_name="Base de Datos ", header=1, engine='openpyxl')
    df_mst.columns = df_mst.columns.astype(str).str.strip()

    col_diseno = next((c for c in df_mst.columns if "DISEÑO" in c.upper()), None)

    if col_diseno:
        for _, row in df_mst.iterrows():
            cod = str(row[col_diseno]).strip()
            if cod in ['', 'nan', '-']:
                continue

            cursor.execute("""
                INSERT OR REPLACE INTO recetas (
                    codigo_diseno, cemento_kg, arena_kg, grava_kg, agua_kg,
                    aditivo_a, aditivo_b, aditivo_delvo,
                    aditivo_glenium_7950, aditivo_glenium_7970, aditivo_fibras
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                cod,
                limpiar_numero(row.get(COLUMNAS_RECETAS["cemento_kg"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["arena_kg"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["grava_kg"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["agua_kg"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["aditivo_a"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["aditivo_b"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["aditivo_delvo"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["aditivo_glenium_7950"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["aditivo_glenium_7970"])),
                limpiar_numero(row.get(COLUMNAS_RECETAS["aditivo_fibras"]))
            ))

    conn.commit()
    conn.close()
    print("Migración de datos completada.")

# --------------------------------------------------
# EJECUCIÓN DIRECTA
# --------------------------------------------------
if __name__ == "__main__":
    cargar_datos()
