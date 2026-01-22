from flask import Flask, render_template, jsonify, request, Response
import os
import json
import sqlite3
import logging
import pandas as pd
from utils.loaders import (
    consumo_diario,
    registros_ultima_semana,
    insertar_despacho,
    cruce_consumo_por_rango,
    cruzar_consumo_vs_stock,
    _receta_por_diseno,
    _calcular_consumos_estimados,
    _conectar)
from ml.graficas import graficas_dinamicas
from ed.busquedas import buscar_por_rango, busqueda_diseno_destino
from ml.predictor import predecir_batch, predecir_materiales, obtener_info_modelo

# Configuración Flask
app = Flask(__name__)

DIRECTORIO_BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_BD = os.path.join(DIRECTORIO_BASE, "db", "gestion_materiales.db")
app.config["DATABASE"] = RUTA_BD

logging.basicConfig(level=logging.INFO)

# ===== RUTAS HTML =====

@app.route("/")
def home():
    return "Servidor Flask funcionando"

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/registro")
def registro():
    return render_template("registro.html")

@app.route("/inventario")
def inventario():
    return render_template("inventario.html")

@app.route("/historial")
def historial():
    return render_template("historial.html")

@app.route("/graficas")
def graficas():
    return render_template("graficas.html")

@app.route("/ml")
def ml():
    return render_template("ml_prediccion.html")

# ===== APIS PRINCIPALES =====

@app.route("/api/dashboard")
def api_dashboard():
    """Obtiene datos del dashboard: consumo diario, registros recientes e inventario"""
    try:
        consumo = consumo_diario(ruta_bd=RUTA_BD)
        registros_semanal, cantidad_registros_semanal = registros_ultima_semana(ruta_bd=RUTA_BD)

        # Obtener inventario desde tabla materiales
        with _conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT nombre AS material, unidad, stock_actual AS stock, stock_minimo AS minimo
                FROM materiales
                ORDER BY nombre
            """)
            inventario = [dict(fila) for fila in cursor.fetchall()]

        respuesta = {
            "consumo_diario": consumo,
            "registros_ultima_semana": registros_semanal,
            "cantidad_registros_semana": cantidad_registros_semanal,
            "inventario": inventario,
        }
        return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        logging.exception("Error en /api/dashboard")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/recetas")
def api_recetas():
    """Lista diseños de mezcla disponibles"""
    try:
        with _conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT codigo_diseno FROM recetas ORDER BY codigo_diseno")
            filas = cursor.fetchall()

        disenos = [fila["codigo_diseno"] for fila in filas if fila["codigo_diseno"]]
        return jsonify({"ok": True, "disenos": disenos})
    except Exception as e:
        logging.exception("Error en /api/recetas")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/despachos", methods=["GET", "POST"])
def api_despachos():
    """Maneja registro de despachos de producción"""
    if request.method == "GET":
        return jsonify({"ok": True, "msg": "Endpoint /api/despachos activo. Usa POST para guardar."})

    try:
        datos = request.get_json(force=True) or {}

        fecha = datos.get("fecha", "")
        volumen_m3 = datos.get("volumen_m3", 0)
        diseno_mezcla = datos.get("diseno_mezcla", "")
        zona = datos.get("zona", "")
        wbs = datos.get("wbs", "")
        turno = datos.get("turno", "")
        arena_humedad_pct = datos.get("arena_humedad_pct", 0)
        asentamiento_final_cm = datos.get("asentamiento_final_cm", 0)
        temperatura_c = datos.get("temperatura_c", 0)

        nuevo_id = insertar_despacho(
            fecha=fecha,
            volumen=volumen_m3,
            diseno_mezcla=diseno_mezcla,
            wbs=wbs,
            destino=zona,
            turno=turno,
            humedad_arena=arena_humedad_pct,
            asentamiento_final=asentamiento_final_cm,
            temperatura=temperatura_c,
            ruta_bd=RUTA_BD,
        )

        if not nuevo_id:
            return jsonify({"ok": False, "error": "No se pudo insertar el despacho (revisa validaciones/receta/BD)."}), 400

        return jsonify({"ok": True, "id": nuevo_id})

    except Exception as e:
        logging.exception("Error en /api/despachos")
        return jsonify({"ok": False, "error": f"Error al insertar despacho: {e}"}), 500

# ===== HISTORIAL Y BÚSQUEDAS =====

@app.route("/api/historial_consumo")
def api_historial_consumo():
    """Obtiene historial de consumo con filtros opcionales usando BST/AVL"""
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")
    diseno = request.args.get("diseno") or None
    zona = request.args.get("zona") or None
    turno = request.args.get("turno") or None
    wbs = request.args.get("wbs") or None

    if not inicio or not fin:
        return jsonify({"error": "Debes enviar 'inicio' y 'fin'."}), 400

    try:
        # Búsqueda con estructuras de datos
        filas, tiempo_bst, tiempo_avl = buscar_por_rango(inicio, fin)
        
        # Aplicar filtros adicionales
        if diseno or zona or turno or wbs:
            filas = busqueda_diseno_destino(filas, diseno=diseno, destino=zona, turno=turno, wbs=wbs)

        # Ordenar por fecha e id
        filas.sort(key=lambda x: (x.get("fecha", ""), x.get("id", 0)))
        
        respuesta = {
            "datos": filas,
            "tiempos": {"bst": round(tiempo_bst, 6), "avl": round(tiempo_avl, 6)},
            "total": len(filas),
        }
        return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")

    except Exception as e:
        logging.exception("Error en /api/historial_consumo")
        return jsonify({"error": str(e)}), 500

# ===== GESTIÓN DE MATERIALES =====

@app.route("/api/materiales", methods=["GET", "POST"])
def api_materiales():
    """Gestiona inventario de materiales"""
    if request.method == "GET":
        try:
            with _conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    SELECT id, nombre, unidad, stock_actual, stock_minimo, stock_maximo
                    FROM materiales
                    ORDER BY nombre
                """)
                materiales = [dict(fila) for fila in cursor.fetchall()]
            return jsonify({"ok": True, "materiales": materiales})
        except Exception as e:
            logging.exception("Error en GET /api/materiales")
            return jsonify({"ok": False, "error": str(e)}), 500
    
    # POST: actualizar stock
    try:
        datos = request.get_json(force=True) or {}
        material_id = datos.get("id")
        stock_actual = datos.get("stock_actual")
        stock_minimo = datos.get("stock_minimo")
        
        if not material_id:
            return jsonify({"ok": False, "error": "Falta el ID del material"}), 400
        
        with _conectar() as conexion:
            actualizaciones = []
            parametros = []
            
            if stock_actual is not None:
                actualizaciones.append("stock_actual = ?")
                parametros.append(float(stock_actual))
            
            if stock_minimo is not None:
                actualizaciones.append("stock_minimo = ?")
                parametros.append(float(stock_minimo))
            
            if not actualizaciones:
                return jsonify({"ok": False, "error": "No hay datos para actualizar"}), 400
            
            parametros.append(material_id)
            sql = f"UPDATE materiales SET {', '.join(actualizaciones)} WHERE id = ?"
            
            cursor = conexion.cursor()
            cursor.execute(sql, parametros)
            conexion.commit()
            
            if cursor.rowcount == 0:
                return jsonify({"ok": False, "error": "Material no encontrado"}), 404
        
        return jsonify({"ok": True, "mensaje": "Material actualizado"})
    
    except Exception as e:
        logging.exception("Error en POST /api/materiales")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== RESUMEN DE CONSUMO =====

@app.route("/api/resumen_consumo")
def api_resumen_consumo():
    """Obtiene resumen de consumo por rango de fechas"""
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")
    diseno = request.args.get("diseno") or None
    zona = request.args.get("zona") or None
    turno = request.args.get("turno") or None
    wbs = request.args.get("wbs") or None

    if not inicio or not fin:
        return jsonify({"ok": False, "error": "Debes enviar inicio y fin"}), 400

    try:
        resumen = cruce_consumo_por_rango(
            inicio,
            fin,
            diseno=diseno,
            zona=zona,
            turno=turno,
            wbs=wbs,
            ruta_bd=RUTA_BD,
        )
        return jsonify({"ok": True, "resumen": resumen})
    except Exception as e:
        logging.exception("Error en /api/resumen_consumo")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== CRUCE CONSUMO VS STOCK =====

@app.route("/api/cruce_consumo_registro", methods=["POST"])
def api_cruce_consumo_registro():
    """Calcula cruce consumo vs stock para un registro específico"""
    try:
        datos = request.get_json(force=True)
        logging.warning(f"Payload recibido en cruce_consumo_registro: {datos}")
        
        if not datos:
            return jsonify({"ok": False, "error": "No se recibieron datos"}), 400
        
        diseno = datos.get("diseno_mezcla")
        volumen = datos.get("volumen_m3")
        logging.warning(f"diseno_mezcla: {diseno}, volumen_m3: {volumen} (type: {type(volumen)})")
        
        if not diseno or not volumen:
            return jsonify({"ok": False, "error": "Faltan diseno_mezcla o volumen"}), 400
        
        with _conectar(RUTA_BD) as conexion:
            receta = _receta_por_diseno(conexion, diseno)
            logging.warning(f"Receta obtenida: {receta}")
            
            if receta is None:
                return jsonify({"ok": False, "error": f"No existe receta para {diseno}"}), 400
            
            consumos = _calcular_consumos_estimados(receta, float(volumen))
            logging.warning(f"Consumos calculados: {consumos}")
        
        salida, no_mapeados, no_encontrados = cruzar_consumo_vs_stock(consumos)
        logging.warning(f"OUT cruce consumo vs stock: {salida}")
        
        return jsonify({"ok": True, "datos": salida, "no_mapeados": no_mapeados, "no_encontrados": no_encontrados})
    
    except Exception as e:
        logging.exception("Error en cruce_consumo_registro")
        return jsonify({"ok": False, "error": str(e)}), 500

# Continúa en Parte 3...
# Continuación final de app.py - Parte 3

# ===== GRÁFICAS =====

@app.route("/api/graficas")
def api_graficas():
    """Genera gráficas dinámicas avanzadas desde ml/graficas_finales"""
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")
    diseno = request.args.get("diseno") or None
    zona = request.args.get("zona") or None
    turno = request.args.get("turno") or None
    wbs = request.args.get("wbs") or None

    if not inicio or not fin:
        return jsonify({"ok": False, "error": "Debes enviar inicio y fin"}), 400

    try:
        filas, _, _ = buscar_por_rango(inicio, fin)
        
        if diseno or zona or turno or wbs:
            filas = busqueda_diseno_destino(filas, diseno=diseno, destino=zona, turno=turno, wbs=wbs)
        
        if not filas:
            return jsonify({"ok": True, "graficas": {}, "num_registros": 0})
        
        df = pd.DataFrame(filas)
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        
        figuras = graficas_dinamicas(df)
        
        return jsonify({"ok": True, "graficas": figuras, "num_registros": int(df.shape[0])})
    
    except Exception as e:
        logging.exception("Error en /api/graficas_finales")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== MACHINE LEARNING =====

@app.route("/api/ml/info")
def api_ml_info():
    """Obtiene información del modelo ML"""
    try:
        info = obtener_info_modelo()
        return jsonify(info)
    except FileNotFoundError:
        return jsonify({"error": "Modelo no encontrado", "detalle": "Ejecuta primero ml/MLPFuture.py para entrenar el modelo"}), 404
    except Exception as e:
        return jsonify({"error": f"Error al cargar modelo: {str(e)}"}), 500

@app.route("/api/ml/predecir", methods=["POST"])
def api_ml_predecir():
    """Realiza predicción de materiales para un despacho"""
    try:
        datos = request.get_json(force=True)

        fecha = datos.get("fecha")
        if not fecha:
            return jsonify({"error": 'El campo "fecha" es requerido'}), 400

        turno = datos.get("turno")
        diseno = datos.get("diseno", "OTROS")
        volumen = datos.get("volumen", 6.0)

        try:
            volumen = float(volumen)
            if volumen <= 0:
                return jsonify({"error": "El volumen debe ser mayor a 0"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "El volumen debe ser un número"}), 400

        resultado = predecir_materiales(fecha_str=fecha, turno=turno, diseno=diseno, volumen=volumen)
        return jsonify(resultado)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except FileNotFoundError:
        return jsonify({"error": "Modelo no encontrado", "detalle": "Ejecuta primero ml/MLPFuture.py para entrenar el modelo"}), 404
    except Exception as e:
        return jsonify({"error": f"Error en la predicción: {str(e)}"}), 500

@app.route("/api/ml/predecir_batch", methods=["POST"])
def api_ml_predecir_batch():
    """Realiza múltiples predicciones en lote"""
    try:
        datos = request.get_json(force=True)

        predicciones = datos.get("predicciones", [])
        if not predicciones:
            return jsonify({"error": 'Debes enviar un array de "predicciones"'}), 400

        if not isinstance(predicciones, list):
            return jsonify({"error": '"predicciones" debe ser un array'}), 400

        resultado = predecir_batch(predicciones)
        return jsonify(resultado)

    except FileNotFoundError:
        return jsonify({"error": "Modelo no encontrado", "detalle": "Ejecuta primero ml/MLPFuture.py para entrenar el modelo"}), 404
    except Exception as e:
        return jsonify({"error": f"Error en predicción batch: {str(e)}"}), 500

# ===== INICIAR SERVIDOR =====

if __name__ == "__main__":
    app.run(debug=True)