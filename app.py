from flask import Flask, render_template, jsonify, request, Response, redirect, url_for, session
import os
import json
import logging
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from auth.decoradores import login_required
from utils.db import conectar, RUTA_BD
from services.dashboard import consumo_diario, registros_ultima_semana
from services.despachos import insertar_despacho, _receta_por_diseno, _calcular_consumos_estimados
from services.historial import obtener_historial_consumo, cruce_consumo_por_rango
from services.inventario import obtener_materiales, actualizar_material, cruzar_consumo_vs_stock

load_dotenv()

# Configuración Flask
app = Flask(__name__)
app.config["DATABASE"] = RUTA_BD
app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY no definida. Revisa tu archivo .env")

# ===== COOKIES DE SESIÓN SEGURAS =====
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "ph_session"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600

# ===== RATE LIMITING =====
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],          # sin límite global, solo donde lo apliquemos
    storage_uri="memory://"
)

logging.basicConfig(level=logging.INFO)

# ===== HEADERS DE SEGURIDAD =====
@app.after_request
def agregar_headers_seguridad(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ===== RUTAS HTML =====

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/registro")
@login_required
def registro():
    return render_template("registro.html")

@app.route("/inventario")
@login_required
def inventario():
    return render_template("inventario.html")

@app.route("/historial")
@login_required
def historial():
    return render_template("historial.html")

# ===== API DASHBOARD =====

@app.route("/api/dashboard")
@login_required
def api_dashboard():
    """Datos del dashboard: consumo diario, registros recientes e inventario"""
    try:
        consumo = consumo_diario(ruta_bd=RUTA_BD)
        registros_semanal, cantidad_registros_semanal = registros_ultima_semana(ruta_bd=RUTA_BD)

        with conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT nombre AS material, unidad, stock_actual AS stock, stock_minimo AS minimo
                FROM materiales
                ORDER BY nombre
            """)
            inv = [dict(fila) for fila in cursor.fetchall()]

        respuesta = {
            "consumo_diario": consumo,
            "registros_ultima_semana": registros_semanal,
            "cantidad_registros_semana": cantidad_registros_semanal,
            "inventario": inv,
        }
        return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        logging.exception("Error en /api/dashboard")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== API RECETAS =====

@app.route("/api/recetas")
@login_required
def api_recetas():
    """Lista diseños de mezcla disponibles"""
    try:
        with conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT codigo_diseno FROM recetas ORDER BY codigo_diseno")
            filas = cursor.fetchall()
        disenos = [fila["codigo_diseno"] for fila in filas if fila["codigo_diseno"]]
        return jsonify({"ok": True, "disenos": disenos})
    except Exception as e:
        logging.exception("Error en /api/recetas")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== API DESPACHOS =====

@app.route("/api/despachos", methods=["GET", "POST"])
@login_required
def api_despachos():
    """Registro de despachos de producción"""
    if request.method == "GET":
        return jsonify({"ok": True, "msg": "Endpoint activo. Usa POST para guardar."})

    try:
        datos = request.get_json(force=True) or {}
        nuevo_id = insertar_despacho(
            fecha=datos.get("fecha", ""),
            volumen=datos.get("volumen_m3", 0),
            diseno_mezcla=datos.get("diseno_mezcla", ""),
            wbs=datos.get("wbs", ""),
            destino=datos.get("zona", ""),
            turno=datos.get("turno", ""),
            humedad_arena=datos.get("arena_humedad_pct", 0),
            asentamiento_final=datos.get("asentamiento_final_cm", 0),
            temperatura=datos.get("temperatura_c", 0),
            ruta_bd=RUTA_BD,
        )
        if not nuevo_id:
            return jsonify({"ok": False, "error": "No se pudo insertar el despacho."}), 400
        return jsonify({"ok": True, "id": nuevo_id})
    except Exception as e:
        logging.exception("Error en /api/despachos")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== API HISTORIAL =====

@app.route("/api/historial_consumo")
@login_required
def api_historial_consumo():
    """Historial de consumo con filtros usando SQL puro"""
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")

    if not inicio or not fin:
        return jsonify({"error": "Debes enviar 'inicio' y 'fin'."}), 400

    try:
        filas = obtener_historial_consumo(
            inicio, fin,
            diseno=request.args.get("diseno") or None,
            zona=request.args.get("zona") or None,
            turno=request.args.get("turno") or None,
            wbs=request.args.get("wbs") or None,
            ruta_bd=RUTA_BD,
        )
        filas.sort(key=lambda x: (x.get("fecha", ""), x.get("id", 0)))
        respuesta = {
            "datos": filas,
            "total": len(filas),
        }
        return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        logging.exception("Error en /api/historial_consumo")
        return jsonify({"error": str(e)}), 500

# ===== API MATERIALES =====

@app.route("/api/materiales", methods=["GET", "POST"])
@login_required
def api_materiales():
    """Gestión de inventario de materiales"""
    if request.method == "GET":
        try:
            return jsonify({"ok": True, "materiales": obtener_materiales(ruta_bd=RUTA_BD)})
        except Exception as e:
            logging.exception("Error en GET /api/materiales")
            return jsonify({"ok": False, "error": str(e)}), 500

    try:
        datos = request.get_json(force=True) or {}
        material_id = datos.get("id")
        if not material_id:
            return jsonify({"ok": False, "error": "Falta el ID del material"}), 400

        actualizado = actualizar_material(
            material_id=material_id,
            stock_actual=datos.get("stock_actual"),
            stock_minimo=datos.get("stock_minimo"),
            ruta_bd=RUTA_BD,
        )
        if not actualizado:
            return jsonify({"ok": False, "error": "Material no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Material actualizado"})
    except Exception as e:
        logging.exception("Error en POST /api/materiales")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== API RESUMEN CONSUMO =====

@app.route("/api/resumen_consumo")
@login_required
def api_resumen_consumo():
    """Resumen de consumo por rango de fechas"""
    inicio = request.args.get("inicio")
    fin = request.args.get("fin")

    if not inicio or not fin:
        return jsonify({"ok": False, "error": "Debes enviar inicio y fin"}), 400

    try:
        resumen = cruce_consumo_por_rango(
            inicio, fin,
            diseno=request.args.get("diseno") or None,
            zona=request.args.get("zona") or None,
            turno=request.args.get("turno") or None,
            wbs=request.args.get("wbs") or None,
            ruta_bd=RUTA_BD,
        )
        return jsonify({"ok": True, "resumen": resumen})
    except Exception as e:
        logging.exception("Error en /api/resumen_consumo")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== API CRUCE CONSUMO VS STOCK =====

@app.route("/api/cruce_consumo_registro", methods=["POST"])
@login_required
def api_cruce_consumo_registro():
    """Cruce de consumo estimado vs stock para un registro"""
    try:
        datos = request.get_json(force=True)
        if not datos:
            return jsonify({"ok": False, "error": "No se recibieron datos"}), 400

        diseno = datos.get("diseno_mezcla")
        volumen = datos.get("volumen_m3")

        if not diseno or not volumen:
            return jsonify({"ok": False, "error": "Faltan diseno_mezcla o volumen"}), 400

        with conectar(RUTA_BD) as conexion:
            receta = _receta_por_diseno(conexion, diseno)
            if receta is None:
                return jsonify({"ok": False, "error": f"No existe receta para {diseno}"}), 400
            consumos = _calcular_consumos_estimados(receta, float(volumen))

        salida, no_mapeados, no_encontrados = cruzar_consumo_vs_stock(consumos, ruta_bd=RUTA_BD)
        return jsonify({"ok": True, "datos": salida, "no_mapeados": no_mapeados, "no_encontrados": no_encontrados})
    except Exception as e:
        logging.exception("Error en /api/cruce_consumo_registro")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== API LOGIN =====
@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")          # tarea 12
def api_login():
    # Stub temporal — Juan reemplaza el cuerpo de esta función
    return jsonify({"ok": False, "error": "Login no implementado aún"}), 501

# ===== INICIAR SERVIDOR =====

if __name__ == "__main__":
    app.run(debug=True)