# Importar librerías
from flask import Flask, render_template, jsonify, request
from utils.loaders import get_db_connection_flask
import os

# Creación de la instancia de flask para el servidor
app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config["DATABASE"] = os.path.join(BASE_DIR, "db", "gestion_materiales.db")

# Ruta principal
@app.route("/")
def home():
    return "Servidor Flask funcionando"

#Ruta del login
@app.route("/login")
def login():
    return render_template("login.html")

#Ruta del dashboard
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# ======================
# DEFINICIÓN DE APIs
# ======================
@app.route("/api/datos")
def api_datos():
    try:
        conn = get_db_connection_flask()
        # Ajusta el nombre de la tabla si no es "entregas"
        datos = conn.execute("""
            SELECT 
                fecha,
                fuente_cemento,
                diseno_mezcla,
                lote,
                zona,
                wbs,
                volumen_m3,
                turno,
                arena_humedad_pct,
                asentamiento_final_cm,
                temperatura_c
            FROM despachos
        """).fetchall()
        conn.close()

        # Convertir sqlite3.Row a diccionarios
        lista_datos = [dict(row) for row in datos]
        return jsonify(lista_datos)

    except Exception as e:
        return jsonify({"error": str(e)}), 500






# Ejecución del servidor
if __name__ == "__main__":
    app.run(debug=True)