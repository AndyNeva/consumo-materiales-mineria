import sqlite3
import os
import sys

# Permite importar 'auth' al correr el script directamente desde db/
# (igual que scripts/crear_usuarios.py). Sin esto, el import de
# hashear_password falla y el login se rompe.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "gestion_materiales.db"))

# Import real de hashear_password (sin fallback que guarde texto plano).
# Si este import falla, preferimos que el script aborte a guardar
# contraseñas en texto plano que luego no permitiran login.
from auth.login import hashear_password  # noqa: E402

def poblar_insumos_y_base():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=" * 80)
    print("EJECUTANDO: 02_POBLAR_INSUMOS")
    print("=" * 80)

    # 1. Limpiar e insertar Insumos base
    cur.execute("DELETE FROM Insumos")
    print("[OK] Tabla Insumos limpiada.")

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

    cur.executemany("""
        INSERT INTO Insumos (nombre_insumo, unidad, stock_actual, stock_minimo, stock_maximo)
        VALUES (?, ?, ?, ?, ?)
    """, materiales)
    print(f"[OK] Insertados {len(materiales)} insumos base en catálogo.")

    # 2. Crear usuarios iniciales con contraseña hasheada.
    #    MISMO patrón que scripts/crear_usuarios.py:
    #      - hashear_password real (Werkzeug pbkdf2:sha256)
    #      - UPSERT con ON CONFLICT(username) DO UPDATE
    #      - sin INSERT OR REPLACE (que rompería FOREIGN KEYs de movimientos)
    #      - sin fallback a texto plano
    USUARIOS_INICIALES = [
        ("admin", "admin123", "Admin"),
        ("operador", "operador123", "Operador"),
        ("visor", "visor123", "Visualizador"),
    ]

    print("\nCreando usuarios iniciales...")
    for username, password, rol in USUARIOS_INICIALES:
        pw_hash = hashear_password(password)
        cur.execute(
            """
            INSERT INTO usuarios (username, rol, password_hash)
            VALUES (?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                rol = excluded.rol,
                password_hash = excluded.password_hash
            """,
            (username, rol, pw_hash),
        )
        print(f"  [OK] Usuario '{username}' listo (rol: {rol})")

    conn.commit()
    conn.close()
    print("=" * 80)
    print("[OK] FASE 02 MIGRACIÓN FINALIZADA EXITOSAMENTE")
    print("=" * 80)

if __name__ == "__main__":
    poblar_insumos_y_base()
