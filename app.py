# Importar librerías
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
from utils.loaders import (
    consumo_diario,
    registros_ultima_semana,
    insertar_despacho,
    cargar_datos_tabla,
    cruce_consumo_por_rango,
    cruzar_consumo_vs_stock,
)
from ed.busquedas import buscar_por_rango, busqueda_diseno_destino
from ml.estadisticas_dinamicas import generar_graficas_desde_datos
from ml.predictor import predecir_materiales, obtener_info_modelo, predecir_batch
import pandas as pd
import os
import json

# Creación de la instancia de flask para el servidor
app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config["DATABASE"] = os.path.join(BASE_DIR, "db", "gestion_materiales.db")


# Ruta principal
@app.route("/")
def home():
    return "Servidor Flask funcionando"


# Rutas HTML
@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/registro")
def registro():
    return render_template("registro.html")


@app.route("/historial")
def historial():
    return render_template("historial.html")


@app.route("/inventario")
def inventario():
    return render_template("inventario.html")


# -------------------
# Helpers de API
# -------------------

def _build_historial_response(inicio, fin, diseno=None, destino=None):
    """
    Construye la respuesta JSON del historial con tiempos BST/AVL.
    Se usa tanto en /api/historial como en /api/historial_consumo (alias).
    """
    if not inicio or not fin:
        return jsonify({"error": "Debes enviar 'inicio' y 'fin'."}), 400

    # 1) Filtrar por rango de fechas
    busqueda = buscar_por_rango(inicio, fin)
    resultados_fecha = busqueda[0]

    # 2) Filtrar por diseño y/o destino si aplica
    resultados = busqueda_diseno_destino(
        resultados_fecha,
        diseno=diseno if diseno else None,
        destino=destino if destino else None
    )

    # Normalizar orden de campos
    orden = [
        "id", "fecha", "fuente_cemento", "diseno_mezcla", "lote", "zona", "wbs",
        "volumen_m3", "turno", "arena_humedad_pct", "asentamiento_final_cm", "temperatura_c",
        "arena_kg", "grava_kg", "cemento_he_kg", "cemento_ip_kg", "agua_kg",
        "aditivo_rheo_sika115", "aditivo_basf_sika200", "aditivo_delvo",
        "aditivo_glenium_7950", "aditivo_glenium_7970", "aditivo_fibras"
    ]

    resultados_ordenados = [{campo: r.get(campo) for campo in orden} for r in resultados]

    respuesta = {
        "datos": resultados_ordenados,
        "tiempos": {
            "bst": round(busqueda[1], 6),
            "avl": round(busqueda[2], 6)
        },
        "total": len(resultados_ordenados)
    }

    return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")


# -------------------
# APIs
# -------------------

@app.route("/api/graficas")
def api_graficas():
    """
    API endpoint para generar gráficas dinámicas basadas en búsquedas filtradas.
    
    Parámetros requeridos:
    - inicio: Fecha inicial (YYYY-MM-DD)
    - fin: Fecha final (YYYY-MM-DD)
    
    Parámetros opcionales:
    - diseno: Diseño de mezcla
    - zona: Zona/destino
    - chart_name: Nombre de gráfica específica (si se quiere solo una)
    
    Retorna solo las gráficas apropiadas según la cantidad de datos:
    - 1+ registros: Tablas de resumen
    - 5+ registros: Frecuencia de diseños
    - 10+ registros: Boxplots
    - 30+ registros: Histogramas
    - 50+ registros: Matrices de correlación
    """
    # Obtener parámetros
    inicio = request.args.get('inicio')
    fin = request.args.get('fin')
    diseno = request.args.get('diseno')
    zona = request.args.get('zona')
    chart_name = request.args.get('chart_name')
    
    # Validar parámetros requeridos
    if not inicio or not fin:
        return jsonify({'error': 'Debes enviar "inicio" y "fin"'}), 400
    
    try:
        # 1) Buscar datos por rango
        busqueda = buscar_por_rango(inicio, fin)
        resultados_fecha = busqueda[0]
        
        # 2) Filtrar por diseño y/o zona si aplica
        resultados = busqueda_diseno_destino(
            resultados_fecha,
            diseno=diseno if diseno else None,
            destino=zona if zona else None
        )
        
        # 3) Validar que hay resultados
        if not resultados:
            return jsonify({
                'error': 'No se encontraron registros con los filtros aplicados',
                'num_registros': 0,
                'graficas': {},
                'graficas_disponibles': []
            }), 404
        
        # 4) Convertir a DataFrame
        df = pd.DataFrame(resultados)
        
        # 5) Generar gráficas apropiadas según cantidad de datos
        resultado = generar_graficas_desde_datos(df)
        
        # 6) Extraer solo las gráficas generadas
        graficas = resultado['graficas']
        
        # 7) Si se solicita una gráfica específica
        if chart_name:
            if chart_name not in graficas:
                return jsonify({
                    'error': f'Gráfica "{chart_name}" no disponible para esta búsqueda',
                    'graficas_disponibles': list(graficas.keys()),
                    'num_registros': len(resultados)
                }), 404
            return jsonify({
                chart_name: graficas[chart_name],
                'num_registros': len(resultados)
            })
        
        # 8) Retornar todas las gráficas generadas
        return jsonify({
            'graficas': graficas,
            'graficas_disponibles': list(graficas.keys()),
            'total': len(graficas),
            'num_registros': len(resultados)
        })
    
    except Exception as e:
        return jsonify({'error': f'Error al generar gráficas: {str(e)}'}), 500


@app.route("/api/historial")
def api_historial():
    """
    Endpoint oficial del historial.
    """
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")
    diseno = request.args.get("diseno")
    destino = request.args.get("zona")  # UI suele enviar como zona

    return _build_historial_response(inicio, fin, diseno=diseno, destino=destino)


@app.route("/api/historial_consumo")
def api_historial_consumo():
    """
    Alias para compatibilidad con JS que llama /api/historial_consumo.
    """
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")

    diseno = request.args.get("diseno") or request.args.get("diseno_mezcla")
    destino = request.args.get("zona") or request.args.get("destino")

    return _build_historial_response(inicio, fin, diseno=diseno, destino=destino)


@app.route("/api/dashboard")
def api_dashboard():
    consumo = consumo_diario()
    registros_semanal, cantidad_registros_semanal = registros_ultima_semana()

    respuesta = {
        "consumo_diario": consumo,
        "registros_ultima_semana": registros_semanal,
        "cantidad_registros_semana": cantidad_registros_semanal
    }

    return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")


@app.route("/api/recetas")
def api_recetas():
    """
    Devuelve lista de diseños disponibles desde tabla recetas (codigo_diseno).
    """
    try:
        recetas = cargar_datos_tabla("recetas")
        disenos = []
        for r in recetas:
            val = r.get("codigo_diseno") or r.get("diseno_mezcla") or r.get("codigo") or r.get("diseno")
            if val:
                disenos.append(val)
        disenos = sorted(list(set(disenos)))
        return jsonify({"ok": True, "disenos": disenos})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/despachos", methods=["GET", "POST"])
def api_despachos():
    """
    POST: guarda despacho en DB usando insertar_despacho()
    GET: endpoint informativo.
    """
    if request.method == "GET":
        return jsonify({"ok": True, "msg": "Endpoint /api/despachos activo. Usa POST para guardar."})

    try:
        data = request.get_json(force=True)

        fecha = data.get("fecha")
        volumen = data.get("volumen_m3") if data.get("volumen_m3") is not None else data.get("volumen")
        diseno = data.get("diseno_mezcla")
        wbs = data.get("wbs")

        destino = data.get("zona") if data.get("zona") is not None else data.get("destino")
        turno = data.get("turno")

        humedad_arena = data.get("arena_humedad_pct")
        asentamiento_final = data.get("asentamiento_final_cm")
        temperatura = data.get("temperatura_c")

        despacho_id = insertar_despacho(
            fecha=fecha,
            volumen=volumen,
            diseno_mezcla=diseno,
            wbs=wbs,
            destino=destino,
            turno=turno,
            humedad_arena=humedad_arena,
            asentamiento_final=asentamiento_final,
            temperatura=temperatura,
        )

        if not despacho_id:
            return jsonify({"ok": False, "error": "No se pudo insertar el despacho. Revisa logs de Flask."}), 400

        return jsonify({"ok": True, "id": despacho_id})

    except Exception as e:
        return jsonify({"ok": False, "error": f"Error al insertar despacho: {e}"}), 500


@app.route("/api/alertas_consumo")
def api_alertas_consumo():
    """
    Cruce consumo vs stock (Paso 3).
    """
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")

    if not inicio or not fin:
        return jsonify({"ok": False, "error": "Debes enviar inicio y fin"}), 400

    try:
        resumen = cruce_consumo_por_rango(inicio, fin)
        filas, no_mapeados, no_encontrados = cruzar_consumo_vs_stock(resumen)

        return jsonify({
            "ok": True,
            "inicio": inicio,
            "fin": fin,
            "filas": filas,
            "no_mapeados": no_mapeados,
            "no_encontrados": no_encontrados,
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/resumen_consumo")
def api_resumen_consumo():
    """
    Endpoint que tu historial está llamando (según consola).
    Devuelve el resumen de consumo por rango (base para el cruce y/o para tablas/gráficas).
    """
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")

    if not inicio or not fin:
        return jsonify({"ok": False, "error": "Debes enviar inicio y fin"}), 400

    try:
        resumen = cruce_consumo_por_rango(inicio, fin)
        # Devuelve tal cual para que el JS pinte lo que necesite
        return jsonify({"ok": True, "inicio": inicio, "fin": fin, "resumen": resumen})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# -------------------
# APIs de Predicción ML
# -------------------

@app.route("/api/ml/info")
def api_ml_info():
    """
    Obtiene información sobre el modelo de Machine Learning cargado.
    
    Retorna:
    - Nombre del modelo
    - Diseños de mezcla disponibles
    - Rango de fechas de entrenamiento
    - Métricas de desempeño (R², MAE, RMSE)
    """
    try:
        info = obtener_info_modelo()
        return jsonify(info)
    except FileNotFoundError:
        return jsonify({
            'error': 'Modelo no encontrado',
            'detalle': 'Ejecuta primero ml/MLPFuture.py para entrenar el modelo'
        }), 404
    except Exception as e:
        return jsonify({'error': f'Error al cargar modelo: {str(e)}'}), 500


@app.route("/api/ml/predecir", methods=["POST"])
def api_ml_predecir():
    """
    Predice las cantidades de materiales necesarios para una fecha futura.
    
    Body (JSON):
    - fecha: Fecha en formato 'YYYY-MM-DD' (requerido)
    - turno: 'DIA', 'NOCHE', 'AMBOS' o null (opcional, si es null calcula ambos turnos y suma)
    - diseno: Diseño de mezcla (opcional, default: 'OTROS')
    - volumen: Volumen en m³ (opcional, default: 6.0)
    
    Retorna:
    - Predicción de Arena (kg), Grava (kg), Cemento (kg)
    - Si turno=AMBOS o null, incluye desglose por turno
    """
    try:
        data = request.get_json(force=True)
        
        fecha = data.get('fecha')
        if not fecha:
            return jsonify({'error': 'El campo "fecha" es requerido'}), 400
        
        turno = data.get('turno')  # Puede ser None
        diseno = data.get('diseno', 'OTROS')
        volumen = data.get('volumen', 6.0)
        
        # Validar volumen
        try:
            volumen = float(volumen)
            if volumen <= 0:
                return jsonify({'error': 'El volumen debe ser mayor a 0'}), 400
        except (TypeError, ValueError):
            return jsonify({'error': 'El volumen debe ser un número'}), 400
        
        resultado = predecir_materiales(
            fecha_str=fecha,
            turno=turno,
            diseno=diseno,
            volumen=volumen
        )
        
        return jsonify(resultado)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except FileNotFoundError:
        return jsonify({
            'error': 'Modelo no encontrado',
            'detalle': 'Ejecuta primero ml/MLPFuture.py para entrenar el modelo'
        }), 404
    except Exception as e:
        return jsonify({'error': f'Error en la predicción: {str(e)}'}), 500


@app.route("/api/ml/predecir_batch", methods=["POST"])
def api_ml_predecir_batch():
    """
    Realiza múltiples predicciones en una sola llamada.
    
    Body (JSON):
    - predicciones: Array de objetos con {fecha, turno, diseno, volumen}
    
    Ejemplo:
    {
      "predicciones": [
        {"fecha": "2026-03-01", "turno": "DIA", "diseno": "H25", "volumen": 6},
        {"fecha": "2026-03-02", "turno": "NOCHE", "diseno": "H30", "volumen": 8}
      ]
    }
    
    Retorna:
    - Lista de predicciones exitosas
    - Lista de errores (si hubo)
    - Contadores de éxito/error
    """
    try:
        data = request.get_json(force=True)
        
        predicciones = data.get('predicciones', [])
        if not predicciones:
            return jsonify({'error': 'Debes enviar un array de "predicciones"'}), 400
        
        if not isinstance(predicciones, list):
            return jsonify({'error': '"predicciones" debe ser un array'}), 400
        
        resultado = predecir_batch(predicciones)
        return jsonify(resultado)
        
    except FileNotFoundError:
        return jsonify({
            'error': 'Modelo no encontrado',
            'detalle': 'Ejecuta primero ml/MLPFuture.py para entrenar el modelo'
        }), 404
    except Exception as e:
        return jsonify({'error': f'Error en predicción batch: {str(e)}'}), 500


# Ejecución del servidor
if __name__ == "__main__":
    app.run(debug=True)
