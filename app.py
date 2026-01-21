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
    obtener_historial_consumo,
)

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

        respuesta = {
            "consumo_diario": consumo,
            "registros_ultima_semana": registros_semanal,
            "cantidad_registros_semana": cantidad_registros_semanal,
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
    t0 = time.time()

    inicio = request.args.get("inicio")
    fin = request.args.get("fin")
    diseno = request.args.get("diseno") or None
    zona = request.args.get("zona") or None
    turno = request.args.get("turno") or None
    wbs = request.args.get("wbs") or None

    if not inicio or not fin:
        return jsonify({"error": "Debes enviar 'inicio' y 'fin'."}), 400

    try:
        filas = obtener_historial_consumo(
            inicio,
            fin,
            diseno=diseno,
            zona=zona,
            turno=turno,
            wbs=wbs,
            db_path=DB_PATH,
        )

        bst = time.time() - t0

        resp = {
            "datos": filas,
            "tiempos": {"bst": round(bst, 6), "avl": 0.0},
            "total": len(filas),
        }
        return Response(json.dumps(resp, ensure_ascii=False), mimetype="application/json")

    except Exception as e:
        logging.exception("Error en /api/historial_consumo")
        return jsonify({"error": str(e)}), 500


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


@app.route("/api/alertas_consumo")
def api_alertas_consumo():
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

        filas, no_mapeados, no_encontrados = cruzar_consumo_vs_stock(resumen, db_path=DB_PATH)

        return jsonify({
            "ok": True,
            "filas": filas,
            "no_mapeados": no_mapeados,
            "no_encontrados": no_encontrados,
        })
    except Exception as e:
        logging.exception("Error en /api/alertas_consumo")
        return jsonify({"ok": False, "error": str(e)}), 500


# -------------------------
# Gráficas (Plotly)
# -------------------------
def _plotly_template_dark():
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": "rgba(255,255,255,.92)"},
        "xaxis": {"gridcolor": "rgba(255,255,255,.08)", "zerolinecolor": "rgba(255,255,255,.10)"},
        "yaxis": {"gridcolor": "rgba(255,255,255,.08)", "zerolinecolor": "rgba(255,255,255,.10)"},
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
    }


@app.route("/api/graficas")
def api_graficas():
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")
    diseno = request.args.get("diseno") or None
    zona = request.args.get("zona") or None
    turno = request.args.get("turno") or None
    wbs = request.args.get("wbs") or None

    if not inicio or not fin:
        return jsonify({"ok": False, "error": "Debes enviar inicio y fin"}), 400

    try:
        filas = obtener_historial_consumo(
            inicio, fin,
            diseno=diseno,
            zona=zona,
            turno=turno,
            wbs=wbs,
            db_path=DB_PATH,
        )

        if not filas:
            return jsonify({"ok": True, "figs": {}, "num_registros": 0, "graficas_disponibles": []})

        df = pd.DataFrame(filas)
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

        # 1) Volumen por día
        g1 = df.dropna(subset=["fecha"]).groupby(df["fecha"].dt.date)["volumen_m3"].sum().reset_index()
        fig_vol_dia = {
            "data": [{"type": "bar", "x": [str(x) for x in g1["fecha"]], "y": [float(v) for v in g1["volumen_m3"]]}],
            "layout": {"title": "Volumen por día (m³)", **_plotly_template_dark()},
        }

        # 2) Volumen por diseño
        g2 = df.groupby("diseno_mezcla")["volumen_m3"].sum().reset_index().sort_values("volumen_m3", ascending=False)
        fig_vol_diseno = {
            "data": [{"type": "bar", "x": g2["diseno_mezcla"].tolist(), "y": [float(v) for v in g2["volumen_m3"]]}],
            "layout": {"title": "Volumen por diseño (m³)", **_plotly_template_dark()},
        }

        # 3) Consumo total por material (desde resumen)
        resumen = cruce_consumo_por_rango(
            inicio, fin,
            diseno=diseno,
            zona=zona,
            turno=turno,
            wbs=wbs,
            db_path=DB_PATH,
        )

        labels = [
            "Arena (kg)", "Grava (kg)", "Cemento (kg)", "Agua (kg)",
            "Rheo + Sika115", "BASF + Sika200", "Delvo", "Glenium 7950", "Glenium 7970", "Fibras"
        ]
        values = [
            float(resumen.get("arena_kg", 0)),
            float(resumen.get("grava_kg", 0)),
            float(resumen.get("cemento_kg", 0)),
            float(resumen.get("agua_kg", 0)),
            float(resumen.get("aditivo_rheo_sika115", 0)),
            float(resumen.get("aditivo_basf_sika200", 0)),
            float(resumen.get("aditivo_delvo", 0)),
            float(resumen.get("aditivo_glenium_7950", 0)),
            float(resumen.get("aditivo_glenium_7970", 0)),
            float(resumen.get("aditivo_fibras", 0)),
        ]

        fig_consumo_mat = {
            "data": [{"type": "bar", "x": labels, "y": values}],
            "layout": {"title": "Consumo total estimado por material", **_plotly_template_dark()},
        }

        figs = {
            "volumen_por_dia": fig_vol_dia,
            "consumo_por_material": fig_consumo_mat,
            "volumen_por_diseno": fig_vol_diseno,
        }

        return jsonify({
            "ok": True,
            "figs": figs,
            "num_registros": int(df.shape[0]),
            "graficas_disponibles": list(figs.keys())
        })

    except Exception as e:
        logging.exception("Error en /api/graficas")
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


if __name__ == "__main__":
    app.run(debug=True)
