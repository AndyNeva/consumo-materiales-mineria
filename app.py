# app.py
from flask import Flask, render_template, jsonify, request, Response
import os
import json
import time
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
    _calc_consumos_estimados,
    _connect)
from ml.graficas import graficas_dinamicas
from ed.busquedas import buscar_por_rango, busqueda_diseno_destino
from ml.predictor import predecir_batch, predecir_materiales, obtener_info_modelo


# -------------------------------------------------
# Flask
# -------------------------------------------------
app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "gestion_materiales.db")
app.config["DATABASE"] = DB_PATH

logging.basicConfig(level=logging.INFO)


# -------------------------------------------------
# Helpers DB (solo lectura / consultas simples)
# -------------------------------------------------
def _db_connect():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# Rutas HTML
# -------------------------
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


# -------------------------
# APIs
# -------------------------
@app.route("/api/dashboard")
def api_dashboard():
    """
    Devuelve:
    - consumo_diario (m3) de hoy
    - registros_ultima_semana (lista)
    - cantidad_registros_semana (int)
    """
    try:
        consumo = consumo_diario(db_path=DB_PATH)
        registros_semanal, cantidad_registros_semanal = registros_ultima_semana(db_path=DB_PATH)

        # Obtener inventario real desde la tabla materiales
        with _db_connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT nombre AS material, unidad, stock_actual AS stock, stock_minimo AS minimo
                FROM materiales
                ORDER BY nombre
            """)
            inventario = [dict(r) for r in cur.fetchall()]

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
    """
    Lista diseños disponibles desde tabla recetas (codigo_diseno).
    """
    try:
        with _db_connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT codigo_diseno FROM recetas ORDER BY codigo_diseno")
            rows = cur.fetchall()

        disenos = [r["codigo_diseno"] for r in rows if r["codigo_diseno"]]
        return jsonify({"ok": True, "disenos": disenos})
    except Exception as e:
        logging.exception("Error en /api/recetas")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/despachos", methods=["GET", "POST"])
def api_despachos():
    if request.method == "GET":
        return jsonify({"ok": True, "msg": "Endpoint /api/despachos activo. Usa POST para guardar."})

    try:
        payload = request.get_json(force=True) or {}

        fecha = payload.get("fecha", "")
        volumen_m3 = payload.get("volumen_m3", 0)
        diseno_mezcla = payload.get("diseno_mezcla", "")
        zona = payload.get("zona", "")          # lo que escribes en "Destino de la producción"
        wbs = payload.get("wbs", "")
        turno = payload.get("turno", "")

        arena_humedad_pct = payload.get("arena_humedad_pct", 0)
        asentamiento_final_cm = payload.get("asentamiento_final_cm", 0)
        temperatura_c = payload.get("temperatura_c", 0)

        # OJO: insertar_despacho() recibe "destino", NO "zona".
        new_id = insertar_despacho(
            fecha=fecha,
            volumen=volumen_m3,
            diseno_mezcla=diseno_mezcla,
            wbs=wbs,
            destino=zona,  # <-- aquí se guarda en columna "zona" de tu BD
            turno=turno,
            humedad_arena=arena_humedad_pct,
            asentamiento_final=asentamiento_final_cm,
            temperatura=temperatura_c,
            db_path=DB_PATH,
        )

        if not new_id:
            return jsonify({"ok": False, "error": "No se pudo insertar el despacho (revisa validaciones/receta/DB)."}), 400

        return jsonify({"ok": True, "id": new_id})

    except Exception as e:
        logging.exception("Error en /api/despachos")
        return jsonify({"ok": False, "error": f"Error al insertar despacho: {e}"}), 500


# -------------------------
# Historial
# -------------------------
@app.route("/api/historial_consumo")
def api_historial_consumo():
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")
    diseno = request.args.get("diseno") or None
    zona = request.args.get("zona") or None
    turno = request.args.get("turno") or None
    wbs = request.args.get("wbs") or None

    if not inicio or not fin:
        return jsonify({"error": "Debes enviar 'inicio' y 'fin'."}), 400

    try:
        # Usar búsqueda con BST/AVL
        filas, tiempo_bst, tiempo_avl = buscar_por_rango(inicio, fin)
        
        # Aplicar filtros adicionales si se especificaron
        if diseno or zona or turno or wbs:
            filas = busqueda_diseno_destino(filas, diseno=diseno, destino=zona, turno=turno, wbs=wbs)

        # Ordenar por fecha ASC y id ASC antes de devolver
        filas.sort(key=lambda x: (x.get("fecha", ""), x.get("id", 0)))
        resp = {
            "datos": filas,
            "tiempos": {"bst": round(tiempo_bst, 6), "avl": round(tiempo_avl, 6)},
            "total": len(filas),
        }
        return Response(json.dumps(resp, ensure_ascii=False), mimetype="application/json")

    except Exception as e:
        logging.exception("Error en /api/historial_consumo")
        return jsonify({"error": str(e)}), 500


@app.route("/api/materiales", methods=["GET", "POST"])
def api_materiales():
    """Gestiona inventario de materiales."""
    if request.method == "GET":
        try:
            with _db_connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, nombre, unidad, stock_actual, stock_minimo, stock_maximo
                    FROM materiales
                    ORDER BY nombre
                """)
                materiales = [dict(r) for r in cur.fetchall()]
            return jsonify({"ok": True, "materiales": materiales})
        except Exception as e:
            logging.exception("Error en GET /api/materiales")
            return jsonify({"ok": False, "error": str(e)}), 500
    
    # POST: actualizar stock de un material
    try:
        payload = request.get_json(force=True) or {}
        material_id = payload.get("id")
        stock_actual = payload.get("stock_actual")
        stock_minimo = payload.get("stock_minimo")
        
        if not material_id:
            return jsonify({"ok": False, "error": "Falta el ID del material"}), 400
        
        with _db_connect() as conn:
            updates = []
            params = []
            
            if stock_actual is not None:
                updates.append("stock_actual = ?")
                params.append(float(stock_actual))
            
            if stock_minimo is not None:
                updates.append("stock_minimo = ?")
                params.append(float(stock_minimo))
            
            if not updates:
                return jsonify({"ok": False, "error": "No hay datos para actualizar"}), 400
            
            params.append(material_id)
            sql = f"UPDATE materiales SET {', '.join(updates)} WHERE id = ?"
            
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            
            if cur.rowcount == 0:
                return jsonify({"ok": False, "error": "Material no encontrado"}), 404
        
        return jsonify({"ok": True, "mensaje": "Material actualizado"})
    
    except Exception as e:
        logging.exception("Error en POST /api/materiales")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/resumen_consumo")
def api_resumen_consumo():
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
            db_path=DB_PATH,
        )
        return jsonify({"ok": True, "resumen": resumen})
    except Exception as e:
        logging.exception("Error en /api/resumen_consumo")
        return jsonify({"ok": False, "error": str(e)}), 500

# Nueva API para gráficas dinámicas desde graficas_finales
@app.route("/api/graficas")
def api_graficas():
    """
    Devuelve las gráficas dinámicas generadas por ml/graficas_finales.py usando los mismos filtros y flujo de datos que /api/graficas.
    Parámetros: inicio, fin, diseno, zona, turno, wbs (opcional, igual que /api/graficas)
    """
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
        logging.exception(f"Dataframe columns: {df.columns.tolist()}")
        figs = graficas_dinamicas(df)
        return jsonify({"ok": True, "graficas": figs, "num_registros": int(df.shape[0])})
    except Exception as e:
        logging.exception("Error en /api/graficas_finales")
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------
# APIs de Predicción ML
# -------------------
@app.route("/api/ml/info")
def api_ml_info():
    try:
        info = obtener_info_modelo()
        return jsonify(info)
    except FileNotFoundError:
        return jsonify({"error": "Modelo no encontrado", "detalle": "Ejecuta primero ml/MLPFuture.py para entrenar el modelo"}), 404
    except Exception as e:
        return jsonify({"error": f"Error al cargar modelo: {str(e)}"}), 500


@app.route("/api/ml/predecir", methods=["POST"])
def api_ml_predecir():
    try:
        data = request.get_json(force=True)

        fecha = data.get("fecha")
        if not fecha:
            return jsonify({"error": 'El campo "fecha" es requerido'}), 400

        turno = data.get("turno")
        diseno = data.get("diseno", "OTROS")
        volumen = data.get("volumen", 6.0)

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
    try:
        data = request.get_json(force=True)

        predicciones = data.get("predicciones", [])
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


@app.route("/api/cruce_consumo_registro", methods=["POST"])
def api_cruce_consumo_registro():
    """
    Recibe los mismos datos que el registro de despacho y retorna el cruce consumo vs stock para esa fila.
    """
    try:
        data = request.get_json(force=True)
        logging.warning(f"Payload recibido en cruce_consumo_registro: {data}")
        if not data:
            return jsonify({"ok": False, "error": "No se recibieron datos"}), 400
        diseno = data.get("diseno_mezcla")
        volumen = data.get("volumen_m3")
        logging.warning(f"diseno_mezcla: {diseno}, volumen_m3: {volumen} (type: {type(volumen)})")
        if not diseno or not volumen:
            return jsonify({"ok": False, "error": "Faltan diseno_mezcla o volumen"}), 400
        with _connect(DB_PATH) as conn:
            receta = _receta_por_diseno(conn, diseno)
            logging.warning(f"Receta obtenida: {receta}")
            if receta is None:
                return jsonify({"ok": False, "error": f"No existe receta para {diseno}"}), 400
            consumos = _calc_consumos_estimados(receta, float(volumen))
            logging.warning(f"Consumos calculados: {consumos}")
        out, no_mapeados, no_encontrados = cruzar_consumo_vs_stock(consumos)
        logging.warning(f"OUT cruce consumo vs stock: {out}")
        return jsonify({"ok": True, "datos": out, "no_mapeados": no_mapeados, "no_encontrados": no_encontrados})
    except Exception as e:
        logging.exception("Error en cruce_consumo_registro")
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
