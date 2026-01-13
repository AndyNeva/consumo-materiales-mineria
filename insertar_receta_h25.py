import sqlite3
from pathlib import Path

# Ruta a tu DB (misma lógica que usas en loaders.py)
DB_PATH = Path(__file__).parent / "db" / "gestion_materiales.db"

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la DB en: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Verifica si ya existe H-25
    cur.execute("SELECT id FROM recetas WHERE codigo_diseno = ?", ("H-25",))
    existe = cur.fetchone()

    if existe:
        print("✅ La receta H-25 ya existe. ID:", existe[0])
        conn.close()
        return

    # 2) Inserta receta H-25 
    receta = (
        "H-25",   # codigo_diseno
        320.0,    # cemento_kg
        750.0,    # arena_kg
        980.0,    # grava_kg
        180.0,    # agua_kg
        1.2,      # aditivo_a
        0.8,      # aditivo_b
        0.0,      # aditivo_delvo
        0.0,      # aditivo_glenium_7950
        0.0,      # aditivo_glenium_7970
        0.0       # aditivo_fibras
    )

    cur.execute("""
        INSERT INTO recetas (
            codigo_diseno,
            cemento_kg, arena_kg, grava_kg, agua_kg,
            aditivo_a, aditivo_b, aditivo_delvo,
            aditivo_glenium_7950, aditivo_glenium_7970,
            aditivo_fibras
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, receta)

    conn.commit()

    cur.execute("SELECT id FROM recetas WHERE codigo_diseno = ?", ("H-25",))
    nuevo = cur.fetchone()
    print("✅ Receta H-25 insertada. ID:", nuevo[0] if nuevo else "No puedo confirmar")

    conn.close()

if __name__ == "__main__":
    main()
