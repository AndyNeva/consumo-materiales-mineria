from flask import Flask, render_template, jsonify, request, Response, redirect, url_for, session
import os
import json
import logging
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from auth.decoradores import login_required
from auth.roles import rol_requerido, solo_admin, admin_u_operador  # control por rol (Juan Ruiz)
from auth.login import autenticar
from auth.usuarios import crear_usuario, listar_usuarios
from utils.db import conectar, RUTA_BD
from services.dashboard import consumo_diario, registros_ultima_semana
from services.despachos import insertar_despacho, _receta_por_diseno, _calcular_consumos_estimados
from services.historial import obtener_historial_consumo, cruce_consumo_por_rango
from services.inventario import obtener_materiales, actualizar_material, agregar_material, cruzar_consumo_vs_stock

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


def numero_no_negativo(valor, nombre_campo):
    """Convierte un valor a float y valida que no sea negativo."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre_campo} debe ser un número válido")
    if numero < 0:
        raise ValueError(f"{nombre_campo} no puede ser negativo")
    return numero


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
@admin_u_operador          # Operador puede agregar registros (Juan Ruiz)
def registro():
    return render_template("registro.html")

@app.route("/inventario")
@admin_u_operador          # Operador puede ver inventario (Juan Ruiz)
def inventario():
    return render_template("inventario.html")

@app.route("/historial")
@admin_u_operador          # Visualizador no accede al historial (Juan Ruiz)
def historial():
    return render_template("historial.html")

@app.route("/usuarios")
@solo_admin
def usuarios():
    return render_template("usuarios.html")

# ===== API USUARIOS =====

@app.route("/api/usuarios", methods=["GET", "POST"])
@solo_admin
def api_usuarios():
    """Lista y crea usuarios del sistema. Solo disponible para Admin."""
    if request.method == "GET":
        try:
            return jsonify({"ok": True, "usuarios": listar_usuarios(ruta_bd=RUTA_BD)})
        except Exception as e:
            logging.exception("Error en GET /api/usuarios")
            return jsonify({"ok": False, "error": str(e)}), 500

    try:
        datos = request.get_json(silent=True) or {}
        resultado = crear_usuario(
            username=datos.get("username", ""),
            password=datos.get("password", ""),
            rol=datos.get("rol", ""),
            ruta_bd=RUTA_BD,
        )

        if not resultado.get("ok"):
            return jsonify({"ok": False, "error": resultado.get("error", "No se pudo crear el usuario.")}), resultado.get("status", 400)

        return jsonify({"ok": True, "usuario": resultado["usuario"], "mensaje": "Usuario creado correctamente."}), 201
    except Exception as e:
        logging.exception("Error en POST /api/usuarios")
        return jsonify({"ok": False, "error": str(e)}), 500


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
@admin_u_operador          # Operador puede agregar registros; Visualizador no (Juan Ruiz)
def api_despachos():
    """Registro de despachos de producción"""
    if request.method == "GET":
        return jsonify({"ok": True, "msg": "Endpoint activo. Usa POST para guardar."})

    try:
        datos = request.get_json(force=True) or {}

        # Validación previa para registros de Operador (Juan Ruiz):
        # antes de confirmar, comprobamos que los datos sean consistentes.
        errores = []
        if not str(datos.get("fecha", "")).strip():
            errores.append("Falta la fecha del despacho.")
        try:
            if float(datos.get("volumen_m3", 0)) <= 0:
                errores.append("El volumen_m3 debe ser mayor que 0.")
        except (TypeError, ValueError):
            errores.append("El volumen_m3 no es un número válido.")
        if not str(datos.get("diseno_mezcla", "")).strip():
            errores.append("Falta el diseño de mezcla.")
        if errores:
            return jsonify({"ok": False, "error": " ".join(errores)}), 400

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
@admin_u_operador          # ver inventario: Admin u Operador (Juan Ruiz)
def api_materiales():
    """Gestión de inventario de materiales.

    GET devuelve el inventario completo. POST crea un material nuevo si no
    recibe id, o actualiza el material existente cuando recibe id. Las acciones
    de creación/edición se mantienen restringidas al rol Admin.
    """
    if request.method == "GET":
        try:
            return jsonify({"ok": True, "materiales": obtener_materiales(ruta_bd=RUTA_BD)})
        except Exception as e:
            logging.exception("Error en GET /api/materiales")
            return jsonify({"ok": False, "error": str(e)}), 500

    # Crear o editar inventario es una acción de administración.
    if session.get("rol") != "Admin":
        return jsonify({"ok": False, "error": "Solo el Administrador puede crear o editar el inventario"}), 403

    try:
        datos = request.get_json(force=True) or {}
        material_id = datos.get("id")

        # Crear nuevo material.
        if not material_id:
            nombre = str(datos.get("nombre", "")).strip()
            unidad = str(datos.get("unidad", "")).strip()

            if not nombre:
                return jsonify({"ok": False, "error": "Falta el nombre del material"}), 400
            if not unidad:
                return jsonify({"ok": False, "error": "Falta la unidad del material"}), 400

            stock_actual = numero_no_negativo(datos.get("stock_actual", 0), "Stock actual")
            stock_minimo = numero_no_negativo(datos.get("stock_minimo", 0), "Stock mínimo")
            stock_maximo = numero_no_negativo(datos.get("stock_maximo", 0), "Stock máximo")

            if stock_maximo and stock_maximo < stock_minimo:
                return jsonify({"ok": False, "error": "El stock máximo no puede ser menor que el mínimo"}), 400

            nuevo_id = agregar_material(
                nombre=nombre,
                unidad=unidad,
                stock_actual=stock_actual,
                stock_minimo=stock_minimo,
                stock_maximo=stock_maximo,
                ruta_bd=RUTA_BD,
            )

            if not nuevo_id:
                return jsonify({"ok": False, "error": "No se pudo crear el material"}), 400

            return jsonify({"ok": True, "id": nuevo_id, "mensaje": "Material creado"}), 201

        # Actualizar mínimos y máximos de un material existente.
        stock_actual = datos.get("stock_actual")
        stock_minimo = datos.get("stock_minimo")
        stock_maximo = datos.get("stock_maximo")

        if stock_actual is not None:
            stock_actual = numero_no_negativo(stock_actual, "Stock actual")
        if stock_minimo is not None:
            stock_minimo = numero_no_negativo(stock_minimo, "Stock mínimo")
        if stock_maximo is not None:
            stock_maximo = numero_no_negativo(stock_maximo, "Stock máximo")

        if stock_minimo is not None and stock_maximo is not None and stock_maximo and stock_maximo < stock_minimo:
            return jsonify({"ok": False, "error": "El stock máximo no puede ser menor que el mínimo"}), 400

        actualizado = actualizar_material(
            material_id=material_id,
            stock_actual=stock_actual,
            stock_minimo=stock_minimo,
            stock_maximo=stock_maximo,
            ruta_bd=RUTA_BD,
        )
        if not actualizado:
            return jsonify({"ok": False, "error": "Material no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Material actualizado"})

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        mensaje = str(e)
        if "UNIQUE constraint failed" in mensaje:
            return jsonify({"ok": False, "error": "Ya existe un material con ese nombre"}), 409
        logging.exception("Error en POST /api/materiales")
        return jsonify({"ok": False, "error": mensaje}), 500


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
        return jsonify({"ok": True, "resumen": resumen, "total_registros": resumen.get("registros", 0)})
    except Exception as e:
        logging.exception("Error en /api/resumen_consumo")
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== API ALERTAS CONSUMO =====

@app.route("/api/alertas_consumo")
@login_required
def api_alertas_consumo():
    """Cruza el consumo filtrado del historial contra el stock disponible."""
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
        filas, no_mapeados, no_encontrados = cruzar_consumo_vs_stock(resumen, ruta_bd=RUTA_BD)
        return jsonify({
            "ok": True,
            "filas": filas,
            "no_mapeados": no_mapeados,
            "no_encontrados": no_encontrados,
            "total_registros": resumen.get("registros", 0),
        })
    except Exception as e:
        logging.exception("Error en /api/alertas_consumo")
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

# ===== API LOGIN ===== (Juan Ruiz @eljuandaruiz)
@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")          # tarea 12 (rate limit general de @AndyNeva)
def api_login():
    """
    Autentica al usuario y abre sesión.

    Complementa el rate limit general con: límite de intentos fallidos +
    bloqueo temporal, límite de longitud de contraseña, hash con Werkzeug y
    consultas parametrizadas (ver auth/login.py).
    """
    datos = request.get_json(silent=True) or {}
    username = datos.get("usuario", "")
    password = datos.get("password", "")
    ip = get_remote_address()

    resultado = autenticar(username, password, ip=ip)

    if not resultado["ok"]:
        # 423 (Locked) si está bloqueado por intentos; 401 si solo son credenciales malas.
        codigo = 423 if resultado.get("bloqueado") else 401
        return jsonify({"ok": False, "error": resultado["error"]}), codigo

    # Login correcto: guardamos identidad y rol en la sesión segura de Flask.
    usuario = resultado["usuario"]
    session.clear()
    session["usuario_id"] = usuario["id"]
    session["username"] = usuario["username"]
    session["rol"] = usuario["rol"]
    session.permanent = True

    return jsonify({"ok": True, "usuario": usuario})


# ===== LOGOUT ===== (Juan Ruiz)
@app.route("/logout")
def logout():
    """Cierra la sesión y vuelve al login."""
    session.clear()
    return redirect(url_for("login"))

# ===== INICIAR SERVIDOR =====

if __name__ == "__main__":
    app.run(debug=True)