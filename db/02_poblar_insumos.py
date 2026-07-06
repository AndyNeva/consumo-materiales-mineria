import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

def poblar_insumos_y_base():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("=" * 80)
    print("EJECUTANDO: 02_POBLAR_INSUMOS")
    print("=" * 80)
    
    # 1. Crear usuario administrador base
    cur.execute(
        "INSERT OR IGNORE INTO usuarios (username, rol) VALUES ('admin', 'Admin')"
    )
    print("[OK] Usuario administrador base registrado.")

    # 2. Limpiar e insertar Insumos base
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
    
    # === Crear usuarios iniciales (integrado aquí, usando hashear_password de auth/login.py) ===
    USUARIOS_INICIALES = [
        ("admin", "admin123", "Admin"),
        ("operador", "operador123", "Operador"),
        ("visor", "visor123", "Visualizador"),
    ]

    # Importar la función de hashing desde auth.login para mantener consistencia
    try:
        from auth.login import hashear_password  # type: ignore
    except Exception:
        # Fallback: si por alguna razón no está disponible, usar identidad (no ideal)
        hashear_password = lambda p: p

    # Upsert de usuarios iniciales con hash de contraseña
    for username, password, rol in USUARIOS_INICIALES:
        try:
            pw_hash = hashear_password(password)
        except Exception:
            pw_hash = password
        try:
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
        except Exception:
            cur.execute(
                "INSERT OR REPLACE INTO usuarios (username, rol, password_hash) VALUES (?, ?, ?)",
                (username, rol, pw_hash),
            )

    conn.commit()
    print(f"[OK] Insertados {len(materiales)} insumos base en catálogo.")
    
    conn.close()
    print("=" * 80)
    print("[OK] FASE 02 MIGRACIÓN FINALIZADA EXITOSAMENTE")
    print("=" * 80)

if __name__ == "__main__":
    poblar_insumos_y_base()
