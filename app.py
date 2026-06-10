from flask import Flask, render_template, jsonify, request, Response, redirect, url_for
import os
import json
import logging
from utils.loaders import (
    consumo_diario,
    registros_ultima_semana,
    insertar_despacho,
    cruce_consumo_por_rango,
    cruzar_consumo_vs_stock,
    _receta_por_diseno,
    _calcular_consumos_estimados,
    _conectar)

# Configuración Flask
app = Flask(__name__)

# Definición de rutas y configuración de la base de datos
DIRECTORIO_BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_BD = os.path.join(DIRECTORIO_BASE, "db", "gestion_materiales.db")
app.config["DATABASE"] = RUTA_BD

# Configuración de logging para registrar eventos y errores
logging.basicConfig(level=logging.INFO)

# ===== RUTAS HTML =====

@app.route("/")
def home():
    # Redirige a la página de login por defecto
    return redirect(url_for("login"))

@app.route("/login")
def login():
    # Renderiza la página de login
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    # Renderiza el dashboard principal
    return render_template("dashboard.html")

@app.route("/registro")
def registro():
    # Renderiza la página de registro de despachos
    return render_template("registro.html")

@app.route("/inventario")
def inventario():
    # Renderiza la página de inventario de materiales
    return render_template("inventario.html")

@app.route("/historial")
def historial():
    # Renderiza la página de historial de consumos
    return render_template("historial.html")

@app.route("/graficas")
def graficas():
    # Renderiza la página de gráficas
    return render_template("graficas.html")

@app.route("/ml")
def ml():
    # Renderiza la página de predicción de materiales (ML)
    return render_template("ml_prediccion.html")

# ===== APIS PRINCIPALES =====

@app.route("/api/dashboard")
def api_dashboard():
    """Obtiene datos del dashboard: consumo diario, registros recientes e inventario"""
    try:

        # Consulta consumo diario y registros de la última semana
        consumo = consumo_diario(ruta_bd=RUTA_BD)
        registros_semanal, cantidad_registros_semanal = registros_ultima_semana(ruta_bd=RUTA_BD)

        # Consulta inventario actual desde la base de datos
        with _conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT nombre AS material, unidad, stock_actual AS stock, stock_minimo AS minimo
                FROM materiales
                ORDER BY nombre
            """)
            inventario = [dict(fila) for fila in cursor.fetchall()]

        # Construye la respuesta en formato JSON
        respuesta = {
            "consumo_diario": consumo,
            "registros_ultima_semana": registros_semanal,
            "cantidad_registros_semana": cantidad_registros_semanal,
            "inventario": inventario,
        }
        return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        # Manejo de errores y logging
        logging.exception("Error en /api/dashboard")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/recetas")
def api_recetas():
    """Lista diseños de mezcla disponibles"""
    try:
        # Consulta los códigos de diseño de mezcla
        with _conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT codigo_diseno FROM recetas ORDER BY codigo_diseno")
            filas = cursor.fetchall()

        disenos = [fila["codigo_diseno"] for fila in filas if fila["codigo_diseno"]]
        return jsonify({"ok": True, "disenos": disenos})
    except Exception as e:
        # Manejo de errores y logging
        logging.exception("Error en /api/recetas")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/despachos", methods=["GET", "POST"])
def api_despachos():
    """Maneja registro de despachos de producción"""
    if request.method == "GET":
        # Solo informa que el endpoint está activo
        return jsonify({"ok": True, "msg": "Endpoint /api/despachos activo. Usa POST para guardar."})

    try:

        # Obtiene los datos enviados en el cuerpo de la petición
        datos = request.get_json(force=True) or {}

        # Extrae los campos esperados del despacho
        fecha = datos.get("fecha", "")
        volumen_m3 = datos.get("volumen_m3", 0)
        diseno_mezcla = datos.get("diseno_mezcla", "")
        zona = datos.get("zona", "")
        wbs = datos.get("wbs", "")
        turno = datos.get("turno", "")
        arena_humedad_pct = datos.get("arena_humedad_pct", 0)
        asentamiento_final_cm = datos.get("asentamiento_final_cm", 0)
        temperatura_c = datos.get("temperatura_c", 0)


        # Inserta el despacho en la base de datos
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


        # Verifica si la inserción fue exitosa
        if not nuevo_id:
            return jsonify({"ok": False, "error": "No se pudo insertar el despacho (revisa validaciones/receta/BD)."}), 400

        return jsonify({"ok": True, "id": nuevo_id})

    except Exception as e:
        # Manejo de errores y logging
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
    # TODO: Usar busquedas SQL
    """
    # Valida que se envíen las fechas
    if not inicio or not fin:
        return jsonify({"error": "Debes enviar 'inicio' y 'fin'."}), 400

    try:

        # Realiza la búsqueda usando estructuras de datos
        filas, tiempo_bst, tiempo_avl = buscar_por_rango(inicio, fin)
        
        # Aplica filtros adicionales si se especifican
        if diseno or zona or turno or wbs:
            filas = busqueda_diseno_destino(filas, diseno=diseno, destino=zona, turno=turno, wbs=wbs)

        # Ordena los resultados por fecha e id
        filas.sort(key=lambda x: (x.get("fecha", ""), x.get("id", 0)))
        
        # Construye la respuesta con los datos y tiempos de búsqueda
        respuesta = {
            "datos": filas,
            "tiempos": {"bst": round(tiempo_bst, 6), "avl": round(tiempo_avl, 6)},
            "total": len(filas),
        }
        return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")

    except Exception as e:
        # Manejo de errores y logging
        logging.exception("Error en /api/historial_consumo")
        return jsonify({"error": str(e)}), 500

        """
        
# ===== GESTIÓN DE MATERIALES =====

@app.route("/api/materiales", methods=["GET", "POST"])
def api_materiales():
    """Gestiona inventario de materiales"""
    if request.method == "GET":
        try:
            # Consulta todos los materiales en la base de datos
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
            # Manejo de errores y logging
            logging.exception("Error en GET /api/materiales")
            return jsonify({"ok": False, "error": str(e)}), 500
    
    # POST: actualizar stock de un material
    try:
        datos = request.get_json(force=True) or {}
        material_id = datos.get("id")
        stock_actual = datos.get("stock_actual")
        stock_minimo = datos.get("stock_minimo")
        
        # Valida que se envíe el ID del material
        if not material_id:
            return jsonify({"ok": False, "error": "Falta el ID del material"}), 400
        
        with _conectar() as conexion:
            actualizaciones = []
            parametros = []
            
            # Prepara los campos a actualizar
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
        # Manejo de errores y logging
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

    # Valida que se envíen las fechas
    if not inicio or not fin:
        return jsonify({"ok": False, "error": "Debes enviar inicio y fin"}), 400

    try:
        # Llama la función para obtener el resumen de consumo
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
        # Manejo de errores y logging
        logging.exception("Error en /api/resumen_consumo")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== CRUCE CONSUMO VS STOCK =====

@app.route("/api/cruce_consumo_registro", methods=["POST"])
def api_cruce_consumo_registro():
    """Calcula cruce consumo vs stock para un registro específico"""
    try:
        # Obtiene los datos enviados en el cuerpo de la petición
        datos = request.get_json(force=True)
        logging.warning(f"Payload recibido en cruce_consumo_registro: {datos}")
        
        if not datos:
            return jsonify({"ok": False, "error": "No se recibieron datos"}), 400
        
        # Extrae los campos necesarios
        diseno = datos.get("diseno_mezcla")
        volumen = datos.get("volumen_m3")
        logging.warning(f"diseno_mezcla: {diseno}, volumen_m3: {volumen} (type: {type(volumen)})")
        
        if not diseno or not volumen:
            return jsonify({"ok": False, "error": "Faltan diseno_mezcla o volumen"}), 400
        
        # Consulta la receta y calcula los consumos estimados
        with _conectar(RUTA_BD) as conexion:
            receta = _receta_por_diseno(conexion, diseno)
            logging.warning(f"Receta obtenida: {receta}")
            
            if receta is None:
                return jsonify({"ok": False, "error": f"No existe receta para {diseno}"}), 400
            
            consumos = _calcular_consumos_estimados(receta, float(volumen))
            logging.warning(f"Consumos calculados: {consumos}")
        
        # Realiza el cruce entre consumos y stock
        salida, no_mapeados, no_encontrados = cruzar_consumo_vs_stock(consumos)
        logging.warning(f"OUT cruce consumo vs stock: {salida}")
        
        return jsonify({"ok": True, "datos": salida, "no_mapeados": no_mapeados, "no_encontrados": no_encontrados})
    
    except Exception as e:
        # Manejo de errores y logging
        logging.exception("Error en cruce_consumo_registro")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== INICIAR SERVIDOR =====

if __name__ == "__main__":
    app.run(debug=True)