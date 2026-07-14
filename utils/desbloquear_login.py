import sqlite3
from db import RUTA_BD

TABLA = "intentos_login"

def borrar_entrada():
    conn = sqlite3.connect(RUTA_BD)
    cursor = conn.cursor()

    clave = input("Ingresa la clave a borrar: ").strip()

    cursor.execute(f"SELECT * FROM {TABLA} WHERE clave = ?", (clave,))
    fila = cursor.fetchone()

    if fila is None:
        print(f"No se encontró ninguna entrada con clave: {clave}")
        conn.close()
        return

    print(f"Entrada encontrada: {fila}")
    confirmar = input("¿Confirmas que quieres borrarla? (s/n): ").strip().lower()

    if confirmar == "s":
        cursor.execute(f"DELETE FROM {TABLA} WHERE clave = ?", (clave,))
        conn.commit()
        print("Entrada borrada correctamente.")
    else:
        print("Operación cancelada.")

    conn.close()

if __name__ == "__main__":
    borrar_entrada()