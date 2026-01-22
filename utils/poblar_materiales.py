"""
Script para poblar la tabla materiales con los datos iniciales
"""
import sqlite3

DB_PATH = "db/gestion_materiales.db"

def poblar_materiales():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("=" * 80)
    print("POBLANDO TABLA MATERIALES")
    print("=" * 80)
    
    # Primero, limpiar la tabla
    cur.execute("DELETE FROM materiales")
    print("\n✓ Tabla limpiada")
    
    # Datos iniciales (usando valores razonables)
    materiales = [
        ("Arena", "kg", 60000, 25000, 100000),
        ("Grava", "kg", 80000, 35000, 120000),
        ("Cemento", "kg", 25000, 12000, 50000),
        ("Agua", "kg", 50000, 10000, 100000),
        ("RHEO 1000", "kg", 1000, 500, 3500),
        ("Sika 115", "kg", 800, 300, 2500),
        ("BASF 719", "kg", 1000, 500, 3500),
        ("Sika 200", "kg", 800, 300, 2500),
        ("Delvo", "l", 112.82, 50, 500),
        ("Glenium 7950", "l", 381.02, 150, 800),
        ("Glenium 7970", "l", 400, 150, 800),
        ("Fibras", "kg", 200, 80, 500),
    ]
    
    # Insertar materiales
    cur.executemany("""
        INSERT INTO materiales (nombre, unidad, stock_actual, stock_minimo, stock_maximo)
        VALUES (?, ?, ?, ?, ?)
    """, materiales)
    
    conn.commit()
    
    print(f"\n✓ Insertados {len(materiales)} materiales:")
    for mat in materiales:
        print(f"  - {mat[0]}: {mat[2]} {mat[1]} (mín: {mat[3]}, máx: {mat[4]})")
    
    # Verificar
    cur.execute("SELECT COUNT(*) as total FROM materiales")
    total = cur.fetchone()[0]
    
    print(f"\n✓ Total de materiales en BD: {total}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✓ TABLA MATERIALES POBLADA EXITOSAMENTE")
    print("=" * 80)

if __name__ == "__main__":
    respuesta = input("¿Poblar la tabla materiales con datos iniciales? (s/n): ")
    if respuesta.lower() == 's':
        poblar_materiales()
    else:
        print("Cancelado.")
