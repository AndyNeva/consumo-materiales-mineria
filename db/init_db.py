import pandas as pd
import sqlite3
import os
import sys

# --- 1. CONFIGURACIÓN Y RUTAS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")
EXCEL_PATH = os.path.join(BASE_DIR, "data", "raw", "Batch_Plant_Production_2025.xlsm")

# --- 2. MAPEO EXACTO DE COLUMNAS ---
# Aquí he pegado LITERALMENTE los nombres que me diste.
COLUMNAS_RECETAS = {
    # Materiales Base
    "cemento_kg":           "CEMENTO",
    "arena_kg":             "Arena (kg)",
    "grava_kg":             "Grava (kg)",
    "agua_kg":              "Agua (kg)",
    
    # Aditivos (Nombres exactos proporcionados)
    "aditivo_a":            "RHEO 1000 (kg)  Sika 115 (kg)",
    "aditivo_b":            "BASF 719 (kg)  Sika 200 (kg)",
    "aditivo_delvo":        "Delvo (litros)",
    "aditivo_glenium_7950": "MasterGlenium 7950",
    "aditivo_glenium_7970": "MasterGlenium 7970",
    "aditivo_fibras":       "Sika PP 48 (kg)-BARCHIP"
}

print(f"🚀 INICIANDO MIGRACIÓN (MODO PRECISIÓN)...")
print(f"📂 Excel: {EXCEL_PATH}")

# --- 3. UTILIDADES ---
def limpiar_numero(valor):
    if isinstance(valor, (int, float)): return float(valor)
    if pd.isna(valor): return 0.0
    val_str = str(valor).strip()
    if val_str in ['-', '', 'nan', 'None']: return 0.0
    multiplicador = 1.0
    if '(' in val_str and ')' in val_str:
        multiplicador = -1.0
        val_str = val_str.replace('(', '').replace(')', '')
    try:
        if ',' in val_str and '.' not in val_str: val_str = val_str.replace(',', '.')
        return float(val_str) * multiplicador
    except ValueError:
        return 0.0

# --- 4. PREPARAR DB ---
if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
        print(f"🗑️ DB anterior eliminada.")
    except PermissionError:
        print("⚠️ Cierra programas que usen la DB.")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Esquema de tablas
cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, rol TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS materiales (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, unidad TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS movimientos (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, material_id INTEGER, cantidad REAL, fecha TEXT, tipo TEXT, proveedor TEXT, detalle TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS despachos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, fuente_cemento TEXT, diseno_mezcla TEXT, lote TEXT, zona TEXT, wbs TEXT, volumen_m3 REAL, turno TEXT, arena_humedad_pct REAL, asentamiento_final_cm REAL, temperatura_c REAL, arena_kg REAL, grava_kg REAL, cemento_he_kg REAL, cemento_ip_kg REAL, agua_kg REAL, aditivo_rheo_sika115 REAL, aditivo_basf_sika200 REAL, aditivo_delvo REAL, aditivo_glenium_7950 REAL, aditivo_glenium_7970 REAL, aditivo_fibras REAL)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS centros_costos (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS zonas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)''')

# Tabla Recetas (Con columnas para los 6 aditivos)
cursor.execute('''
CREATE TABLE IF NOT EXISTS recetas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_diseno TEXT UNIQUE,
    cemento_kg REAL, arena_kg REAL, grava_kg REAL, agua_kg REAL,
    aditivo_a REAL DEFAULT 0, aditivo_b REAL DEFAULT 0,
    aditivo_delvo REAL DEFAULT 0, aditivo_glenium_7950 REAL DEFAULT 0,
    aditivo_glenium_7970 REAL DEFAULT 0, aditivo_fibras REAL DEFAULT 0
)
''')

# Datos Base
cursor.execute("INSERT OR IGNORE INTO usuarios (username, rol) VALUES ('admin', 'Admin')")
cursor.execute("INSERT OR IGNORE INTO materiales (id, nombre, unidad) VALUES (1, 'Cemento', 'Kg'), (2, 'Arena', 'Kg'), (3, 'Grava', 'Kg')")
conn.commit()
print("✅ Tablas creadas.")

# --- 5. CARGA DE DATOS ---
try:
    # A. DESPACHOS
    print("⏳ Cargando Despachos...")
    df_desp = pd.read_excel(EXCEL_PATH, sheet_name="Ingreso_Diario", header=0, engine='openpyxl')
    df_desp.columns = df_desp.columns.str.strip()
    c = 0
    for _, row in df_desp.iterrows():
        fecha = str(row.get('FECHA')).split(' ')[0]
        if pd.isna(row.get('FECHA')) or fecha in ['NaT', 'nan', '', '-']: continue
        
        vals = (
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
            limpiar_numero(row.get('UCEM IP (kg)')),
            limpiar_numero(row.get('Agua (kg)')),
            limpiar_numero(row.get('RHEO 1000 (kg)  Sika 115 (kg)')),
            limpiar_numero(row.get('BASF 719 (kg)  Sika 200 (kg)')),
            limpiar_numero(row.get('Delvo (litros)')),
            limpiar_numero(row.get('MasterGlenium 7950')),
            limpiar_numero(row.get('MasterGlenium 7970')),
            limpiar_numero(row.get('Sika PP 48 (kg)-BARCHIP'))
        )

        cursor.execute("""INSERT INTO despachos (
            fecha, fuente_cemento, diseno_mezcla, lote, zona, wbs, volumen_m3, turno,
            arena_humedad_pct, asentamiento_final_cm, temperatura_c,
            arena_kg, grava_kg, cemento_he_kg, cemento_ip_kg, agua_kg,
            aditivo_rheo_sika115, aditivo_basf_sika200, aditivo_delvo,
            aditivo_glenium_7950, aditivo_glenium_7970, aditivo_fibras
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
        c += 1
    print(f"   ↳ ✅ {c} despachos.")

    # B. INVENTARIO
    print("⏳ Cargando Inventario...")
    df_inv = pd.read_excel(EXCEL_PATH, sheet_name="INGRESOS Y CONSUMO DE AGREGADOS", header=1, engine='openpyxl')
    c = 0
    for _, row in df_inv.iterrows():
        fecha = str(row.iloc[0]).split(' ')[0]
        if pd.isna(row.iloc[0]) or fecha in ['NaT', 'nan', '']: continue
        
        prov = "Desconocido"
        try:
            if str(row.iloc[10]).strip() not in ['-', 'nan', '']: prov = "Armijos"
            elif str(row.iloc[11]).strip() not in ['-', 'nan', '']: prov = "Crusermine"
            elif str(row.iloc[12]).strip() not in ['-', 'nan', '']: prov = "Quiringue"
        except: pass

        movs = [(1,1,'INGRESO'), (2,2,'INGRESO'), (3,3,'INGRESO'), (4,1,'EGRESO'), (5,2,'EGRESO'), (6,3,'EGRESO')]
        for col, mat, tipo in movs:
            cant = limpiar_numero(row.iloc[col])
            if cant > 0:
                cursor.execute("INSERT INTO movimientos (usuario_id, material_id, cantidad, fecha, tipo, proveedor) VALUES (?,?,?,?,?,?)", (1, mat, cant, fecha, tipo, prov))
                c += 1
    print(f"   ↳ ✅ {c} movimientos.")

    # C. RECETAS (USANDO NOMBRES EXACTOS)
    print("⏳ Cargando Recetas...")
    # header=1 es importante porque vimos que la fila 0 estaba vacía
    df_mst = pd.read_excel(EXCEL_PATH, sheet_name="Base de Datos ", header=1, engine='openpyxl')
    
    # IMPORTANTE: Eliminamos espacios al inicio y final de las columnas del Excel para asegurar coincidencia
    df_mst.columns = df_mst.columns.astype(str).str.strip()
    
    col_diseno = next((c for c in df_mst.columns if "DISEÑO" in c.upper()), None)
    c_rec = 0
    
    if col_diseno:
        for _, row in df_mst.iterrows():
            cod = str(row[col_diseno]).strip()
            if cod in ['', 'nan', '-']: continue
            
            # Usamos .get() con el nombre exacto del diccionario
            vals = (
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
            )
            
            sql = '''INSERT OR REPLACE INTO recetas 
                     (codigo_diseno, cemento_kg, arena_kg, grava_kg, agua_kg, 
                      aditivo_a, aditivo_b, aditivo_delvo, aditivo_glenium_7950, aditivo_glenium_7970, aditivo_fibras) 
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)'''
            cursor.execute(sql, vals)
            c_rec += 1
    
    # WBS y Zonas
    col_cc = next((c for c in df_mst.columns if "CENTROS DE COSTO" in c.upper()), None)
    if col_cc:
        for cc in df_mst[col_cc].dropna().unique():
            cursor.execute("INSERT OR IGNORE INTO centros_costos (codigo) VALUES (?)", (str(cc).strip(),))
    col_z = next((c for c in df_mst.columns if "ZONA" in c.upper()), None)
    if col_z:
        for z in df_mst[col_z].dropna().unique():
            cursor.execute("INSERT OR IGNORE INTO zonas (nombre) VALUES (?)", (str(z).strip(),))

    print(f"   ↳ ✅ {c_rec} Recetas (Columnas exactas).")

except Exception as e:
    print(f"❌ ERROR: {e}")
    # Tip para depurar si falla un nombre
    print("TIP: Revisa si hay espacios dobles en los nombres de las columnas del Excel.")

conn.commit()
conn.close()
print("="*40)
print("🏁 ¡MIGRACIÓN COMPLETADA!")