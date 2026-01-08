# Importar librerías
from flask import Flask, render_template, jsonify, request, Response
from utils.loaders import cargar_datos_tabla
from ed.busquedas import buscar_por_rango, busqueda_por_diseno, busqueda_por_destino
import os
import json

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


# DEFINICIÓN DE APIs

@app.route("/api/datos")
def api_datos():
    try:
        datos = cargar_datos_tabla('despachos')
        return jsonify(datos)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# GET  /api/buscar      -> recibe ?texto=
@app.route('/api/buscar')
def api_buscar():
    # Pendiente: confirmar nombres de parámetros con frontend
    q = request.args.get('q')  
    inicio = request.args.get('inicio')
    fin = request.args.get('fin')
    
    if inicio and fin:
        return jsonify(buscar_por_rango(inicio, fin))
    elif q:
        return jsonify(buscar_por_fecha(q))
    else:
        return jsonify([])

@app.route('/api/historial')
def api_historial():
    
    inicio = request.args.get('inicio')
    fin = request.args.get('fin')
    diseno = request.args.get('diseno')
    destino = request.args.get('zona')

    if not inicio or not fin:
        return jsonify({"error": "Debes enviar 'inicio' y 'fin'."}), 400

   # 1. Filtrar por fecha
    busqueda = buscar_por_rango(inicio, fin)
    resultados = busqueda[0]

    # 2. Filtrar por diseño (si se envió)
    if diseno:
        resultados = busqueda_por_diseno(resultados, diseno)

    # 3. Filtrar por destino (si se envió)
    if destino:
        resultados = busqueda_por_destino(resultados, destino)


    # Normalizar orden de campos
    orden = ['id', 'fecha', 'fuente_cemento', 'diseno_mezcla', 'lote', 'zona', 'wbs', 
             'volumen_m3', 'turno', 'arena_humedad_pct', 'asentamiento_final_cm', 'temperatura_c',
             'arena_kg', 'grava_kg', 'cemento_he_kg', 'cemento_ip_kg', 'agua_kg',
             'aditivo_rheo_sika115', 'aditivo_basf_sika200', 'aditivo_delvo',
             'aditivo_glenium_7950', 'aditivo_glenium_7970', 'aditivo_fibras']
    
    resultados_ordenados = [{campo: r.get(campo) for campo in orden} for r in resultados]
    
    respuesta = {
        "datos": resultados_ordenados,
        "tiempos": {
            "bst": round(busqueda[1], 6),
            "avl": round(busqueda[2], 6)
        },
        "total": len(resultados_ordenados)
    }

    return Response(json.dumps(resultados_ordenados, ensure_ascii=False), mimetype='application/json')

# POST /api/agregar     -> recibe JSON (fecha, material, cantidad)
# GET  /api/proyeccion  -> devuelve predicción






# Ejecución del servidor
if __name__ == "__main__":
    app.run(debug=True)