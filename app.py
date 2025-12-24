# Importar librerías
from flask import Flask, render_template

# Creación de la instancia de flask para el servidor
app = Flask(__name__)

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






# Ejecución del servidor
if __name__ == "__main__":
    app.run(debug=True)