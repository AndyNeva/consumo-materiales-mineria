# Importar librerías
from flask import Flask, render_template, jsonify, request, Response
from utils.loaders import consumo_diario, registros_ultima_semana, alertas_inventario, insertar_despacho, consumos_calculados, cambiar_stock, agregar_stock, obtener_estado_materiales
from ed.busquedas import buscar_por_rango, busqueda_diseno_destino
import pandas as pd
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

#Ruta del inventario
@app.route("/inventario")
def dashboard():
    return render_template("inventario.html")

#Ruta del registro
@app.route("/registro")
def dashboard():
    return render_template("registro.html")

#Ruta del historial
@app.route("/historial")
def dashboard():
    return render_template("historial.html")


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

    df = pd.DataFrame(resultados_ordenados)

    # TODO: agregar función graficas
    
    respuesta = {
        "datos": resultados_ordenados,
        "tiempos": {
            "bst": round(busqueda[1], 6),
            "avl": round(busqueda[2], 6)
        },
        "total": len(resultados_ordenados)
    }

    return Response(json.dumps(respuesta, ensure_ascii=False), mimetype='application/json'), 200

# POST /api/agregar     -> recibe JSON (fecha, material, cantidad)
# GET  /api/proyeccion  -> devuelve predicción

@app.route('/api/dashboard')
def api_dashboard():
    consumo = consumo_diario()
    registros_semanal, cantidad_registros_semanal = registros_ultima_semana()

    alertas, alertas_cant = alertas_inventario()


    respuesta ={
        "consumo_diario":consumo,
        "registros_ultima_semana":registros_semanal,
        "cantidad_registros_semana":cantidad_registros_semanal,
        "alertas_inventario": alertas,
        "cantidad_alertas_inventario":alertas_cant
    } 

    return Response(json.dumps(respuesta, ensure_ascii=False), mimetype='application/json'), 200

@app.route('/api/consumos', methods=['POST'])
def api_consumos():
    """API para calcular consumos sin registrar el despacho."""
    try:
        datos = request.get_json()
        
        if not datos:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
        
        diseno_mezcla = datos.get('diseno_mezcla')
        volumen = datos.get('volumen')
        
        if not diseno_mezcla:
            return jsonify({"error": "Falta el diseño de mezcla"}), 400
        
        if not volumen:
            return jsonify({"error": "Falta el volumen"}), 400
        
        try:
            volumen = float(volumen)
            if volumen <= 0:
                return jsonify({"error": "El volumen debe ser mayor a 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "El volumen debe ser un número válido"}), 400
        
        # Calcular consumos
        resultado = consumos_calculados(diseno_mezcla, volumen)
        
        if resultado is None:
            return jsonify({"error": "No se pudieron calcular los consumos. Verifique el diseño de mezcla."}), 400
        
        return Response(json.dumps(resultado, ensure_ascii=False), mimetype='application/json'), 200
        
    except Exception as e:
        return jsonify({"error": f"Error inesperado: {str(e)}"}), 500

@app.route('/api/registro', methods=['POST'])
def api_registro():
    """API para registrar un nuevo despacho y actualizar inventario."""
    try:
        # Obtener datos del request JSON
        datos = request.get_json()
        
        # Validar que se envió JSON
        if not datos:
            return jsonify({
                "error": "No se recibieron datos JSON"}), 400
        
        # Extraer campos requeridos
        fecha = datos.get('fecha')
        volumen = datos.get('volumen')
        diseno_mezcla = datos.get('diseno_mezcla')
        wbs = datos.get('wbs')
        destino = datos.get('destino')
        turno = datos.get('turno')
        humedad_arena = datos.get('humedad_arena')
        asentamiento_final = datos.get('asentamiento_final')
        temperatura = datos.get('temperatura')
        usuario_id = datos.get('usuario_id')
        
        # Validar campos obligatorios
        campos_requeridos = {'fecha': fecha, 'volumen': volumen, 'diseno_mezcla': diseno_mezcla,
            'wbs': wbs, 'destino': destino, 'turno': turno, 'humedad_arena': humedad_arena,
            'asentamiento_final': asentamiento_final, 'temperatura': temperatura}
        
        campos_faltantes = [campo for campo, valor in campos_requeridos.items() if valor is None or valor == '']
        
        if campos_faltantes:
            return jsonify({
                "error": f"Campos requeridos faltantes: {', '.join(campos_faltantes)}"}), 400
        
        # 1. Calcular consumos antes de insertar
        resultado = consumos_calculados(diseno_mezcla, volumen)
        
        if resultado is None:
            return jsonify({
                "error": "No se pudieron calcular los consumos. Verifique el diseño de mezcla."}), 400
        
        # Validar que el stock sea suficiente
        if not resultado.get('stock_suficiente', False):
            return jsonify({
                "error": "Stock insuficiente para realizar el despacho",
                "mensaje": resultado.get('mensaje', ''),
                "consumos": resultado.get('consumos', []),
                "alertas": resultado.get('alertas', []),
                "stock_suficiente": False
            }), 400
        
        consumos = resultado.get('consumos', [])
        
        # 2. Insertar el despacho en la base de datos
        despacho_id = insertar_despacho(fecha, volumen, diseno_mezcla, wbs, destino, turno,
            humedad_arena, asentamiento_final, temperatura)
        
        if despacho_id is None:
            return jsonify({
                "error": "Error al insertar el despacho en la base de datos"}), 500
        
        # 3. Actualizar el stock de materiales
        stock_actualizado = cambiar_stock(diseno_mezcla, volumen, usuario_id)
        
        if not stock_actualizado:
            return jsonify({
                "warning": "Despacho registrado pero no se pudo actualizar el stock",
                "despacho_id": despacho_id,
            }), 201
        
        # 4. Respuesta exitosa
        resultado = {"mensaje": "Despacho registrado exitosamente",
            "despacho_id": despacho_id}
        return Response(json.dumps(resultado, ensure_ascii=False), mimetype='application/json'), 201
        
    except Exception as e:
        return jsonify({
            "error": f"Error inesperado: {str(e)}"
        }), 500

@app.route('/api/materiales/estado')
def api_estado_materiales():
    """API para obtener el estado de todos los materiales en inventario."""
    try:
        materiales = obtener_estado_materiales()
        
        if materiales is None:
            return jsonify({
                "error": "No se pudieron obtener los materiales"
            }), 500
        
        return Response(json.dumps(materiales, ensure_ascii=False), mimetype='application/json'), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Error inesperado: {str(e)}"
        }), 500

@app.route('/api/materiales/agregar', methods=['POST'])
def api_agregar_material():
    """API para agregar stock a un material existente."""
    try:
        datos = request.get_json()
        
        if not datos:
            return jsonify({
                "error": "No se recibieron datos JSON"
            }), 400
        
        # Extraer campos
        material = datos.get('material')
        stock = datos.get('stock')
        unidad = datos.get('unidad')
        usuario_id = datos.get('usuario_id', 1)
        
        # Validar campos requeridos
        if not material:
            return jsonify({
                "error": "El campo 'material' es requerido"
            }), 400
        
        if stock is None:
            return jsonify({
                "error": "El campo 'stock' es requerido"
            }), 400
        
        if not unidad:
            return jsonify({
                "error": "El campo 'unidad' es requerido"
            }), 400
        
        # Validar que stock sea numérico y positivo
        try:
            stock = float(stock)
            if stock < 0:
                return jsonify({
                    "error": "El stock debe ser un valor positivo"
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "error": "El stock debe ser un valor numérico válido"
            }), 400
        
        # Agregar el stock
        material_id = agregar_stock(material, stock, unidad, usuario_id)
        
        if material_id is None:
            return jsonify({
                "error": "No se pudo agregar el stock. Verifique que el material exista."
            }), 500
        
        respuesta = {"mensaje": f"Stock agregado exitosamente a {material}",
            "material_id": material_id}
        
        return Response(json.dumps(respuesta, ensure_ascii=False), mimetype='application/json'), 201
        
    except Exception as e:
        return jsonify({
            "error": f"Error inesperado: {str(e)}"
        }), 500


# Ejecución del servidor
if __name__ == "__main__":
    app.run(debug=True)