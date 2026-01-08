# Importar librerías
from flask import Flask, render_template, jsonify, request, Response
from utils.loaders import consumo_diario, registros_ultima_semana
from ed.busquedas import buscar_por_rango, busqueda_diseno_destino
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
    resultados_fecha = busqueda[0]

    # 2. Filtrar por diseño y/o destino (si se envió)
    resultados = busqueda_diseno_destino(resultados_fecha, 
        diseno=diseno if diseno else None,
        destino=destino if destino else None)


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

    return Response(json.dumps(respuesta, ensure_ascii=False), mimetype='application/json')

# POST /api/agregar     -> recibe JSON (fecha, material, cantidad)
# GET  /api/proyeccion  -> devuelve predicción

@app.route('api/dashboard')
def api_dashboard():
    consumo = consumo_diario()
    registros_semanal, cantidad_registros_semanal = registros_ultima_semana()

    respuesta ={
        "consumo_diario":consumo,
        "registros_ultima_semana":registros_semanal,
        "cantidad_registros_semana":cantidad_registros_semanal
    } 

    return Response(json.dumps(respuesta, ensure_ascii=False), mimetype='application/json')





# Ejecución del servidor
if __name__ == "__main__":
    app.run(debug=True)