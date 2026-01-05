# Importar librerías
from flask import Flask, render_template, jsonify, request
from utils.loaders import cargar_datos_tabla
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
        datos = cargar_datos_tabla('despachos')
        return jsonify(datos)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# GET  /api/buscar      -> recibe ?texto=
# POST /api/agregar     -> recibe JSON (fecha, material, cantidad)
# GET  /api/proyeccion  -> devuelve predicción






# Ejecución del servidor
if __name__ == "__main__":
    app.run(debug=True)