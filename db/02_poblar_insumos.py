import sqlite3
import os
import sys

# Permite importar 'auth' al correr el script directamente desde db/
# (igual que scripts/crear_usuarios.py). Sin esto, el import de
# hashear_password falla y el login se rompe.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

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
    #    Las cédulas son de demostración: pasan el checksum módulo 10 real
    #    (utils/validaciones.py), pero no corresponden a personas reales.
    USUARIOS_INICIALES = [
        ("admin", "admin123", "Admin", "1701234567"),
        ("operador", "operador123", "Operador", "1712345675"),
        ("visor", "visor123", "Visualizador", "0901234567"),
    ]

    print("\nCreando usuarios iniciales...")
    for username, password, rol, cedula in USUARIOS_INICIALES:
        pw_hash = hashear_password(password)
        cur.execute(
            """
            INSERT INTO usuarios (username, rol, password_hash, cedula)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                rol = excluded.rol,
                password_hash = excluded.password_hash,
                cedula = excluded.cedula
            """,
            (username, rol, pw_hash, cedula),
        )
        print(f"  [OK] Usuario '{username}' listo (rol: {rol})")

    conn.commit()
    conn.close()
    print("=" * 80)
    print("[OK] FASE 02 MIGRACIÓN FINALIZADA EXITOSAMENTE")
    print("=" * 80)

if __name__ == "__main__":
    poblar_insumos_y_base()