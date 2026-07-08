from flask import Flask, render_template, jsonify, request, Response, redirect, url_for, session
import os
import json
import logging
import time
from dotenv import load_dotenv
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from auth.roles import cualquier_usuario, solo_admin, admin_u_operador
from auth.login import autenticar
from auth.usuarios import crear_usuario, listar_usuarios
from utils.db import conectar, RUTA_BD
from utils.logging_seguridad import configurar_logging, logger_seguridad
from services.dashboard import consumo_diario, registros_ultima_semana
from services.despachos import insertar_despacho, _receta_por_diseno, _calcular_consumos_estimados
from services.historial import obtener_historial_consumo, cruce_consumo_por_rango
from services.inventario import obtener_materiales, actualizar_material, agregar_material, cruzar_consumo_vs_stock

load_dotenv()

app = Flask(__name__)
app.config["DATABASE"] = RUTA_BD
app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY no definida. Revisa tu archivo .env")

# ===== CSRF PROTECTION =====
csrf = CSRFProtect(app)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "ph_session"

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# ===== Logging centralizado =====
configurar_logging()

# Mensaje genérico reutilizable
MSG_ERROR_GENERICO = "Ocurrió un error al procesar la solicitud. Intenta de nuevo más tarde."
# ===== TIMEOUT DE SESIÓN POR INACTIVIDAD =====
INACTIVIDAD_MAX_SEGUNDOS = 15 * 60  # 15 minutos

@app.before_request
def verificar_inactividad():
    if "usuario_id" in session:
        ahora = time.time()
        ultima = session.get("ultima_actividad", ahora)
        if ahora - ultima > INACTIVIDAD_MAX_SEGUNDOS:
            session.clear()  # sesión vencida por inactividad
        else:
            session["ultima_actividad"] = ahora

logging.basicConfig(level=logging.INFO)


def _float_flexible(valor):
    """Convierte números escritos con punto o coma decimal a float."""
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    return float(valor)


def validar_fecha_iso(valor):
    """Valida una fecha en formato YYYY-MM-DD."""
    if not valor or not isinstance(valor, str):
        return False
    try:
        datetime.strptime(valor, "%Y-%m-%d")
        return True
    except Exception:
        return False


def numero_no_negativo(valor, nombre_campo):
    """Convierte un valor a float y valida que no sea negativo."""
    try:
        numero = _float_flexible(valor)
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
    rutas_protegidas = ("/dashboard", "/registro", "/inventario", "/historial", "/ml")
    if request.path in rutas_protegidas or request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response

# ===== RUTAS HTML =====

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard")
@cualquier_usuario
def dashboard():
    return render_template("dashboard.html")

@app.route("/registro")
@admin_u_operador
def registro():
    return render_template("registro.html")

@app.route("/inventario")
@admin_u_operador
def inventario():
    return render_template("inventario.html")

@app.route("/historial")
@admin_u_operador
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
@cualquier_usuario
def api_dashboard():
    try:
        consumo = consumo_diario(ruta_bd=RUTA_BD)
        registros_semanal, cantidad_registros_semanal = registros_ultima_semana(ruta_bd=RUTA_BD)

        # Obtener inventario desde la capa de servicios y mapear
        # a la estructura que espera el frontend (material, unidad, stock, minimo)
        inv_raw = obtener_materiales(ruta_bd=RUTA_BD)
        inv = [
            {
                "material": m.get("nombre") or m.get("nombre_insumo"),
                "unidad": m.get("unidad"),
                "stock": m.get("stock_actual") if m.get("stock_actual") is not None else m.get("stock", 0),
                "minimo": m.get("stock_minimo") if m.get("stock_minimo") is not None else m.get("minimo", 0),
            }
            for m in (inv_raw or [])
        ]

        respuesta = {
            "consumo_diario": consumo,
            "registros_ultima_semana": registros_semanal,
            "cantidad_registros_semana": cantidad_registros_semanal,
            "inventario": inv,
        }
        return Response(json.dumps(respuesta, ensure_ascii=False), mimetype="application/json")
    except Exception:
        logging.exception("Error en /api/dashboard")
        return jsonify({"ok": False, "error": MSG_ERROR_GENERICO}), 500

# ===== API RECETAS =====

@app.route("/api/recetas")
@cualquier_usuario
def api_recetas():
    try:
        with conectar() as conexion:
            cursor = conexion.cursor()
            # La tabla de diseños se llama `Disenos_Mezcla` en el esquema
            cursor.execute("SELECT diseno_mezcla AS codigo_diseno FROM Disenos_Mezcla ORDER BY diseno_mezcla")
            filas = cursor.fetchall()
        disenos = [fila["codigo_diseno"] for fila in filas if fila["codigo_diseno"]]
        return jsonify({"ok": True, "disenos": disenos})
    except Exception:
        logging.exception("Error en /api/recetas")
        return jsonify({"ok": False, "error": MSG_ERROR_GENERICO}), 500

# ===== API DESPACHOS =====

@app.route("/api/despachos", methods=["GET", "POST"])
@admin_u_operador
def api_despachos():
    if request.method == "GET":
        return jsonify({"ok": True, "msg": "Endpoint activo. Usa POST para guardar."})

    try:
        datos = request.get_json(force=True) or {}

        errores = []
        if not str(datos.get("fecha", "")).strip():
            errores.append("Falta la fecha del despacho.")
        try:
            if _float_flexible(datos.get("volumen_m3", 0)) <= 0:
                errores.append("El volumen_m3 debe ser mayor que 0.")
        except (TypeError, ValueError):
            errores.append("El volumen_m3 no es un número válido.")
        if not str(datos.get("diseno_mezcla", "")).strip():
            errores.append("Falta el diseño de mezcla.")
        if errores:
            logger_seguridad.info(
                "Despacho rechazado por validación | usuario=%s ip=%s errores=%s",
                session.get("username"), request.remote_addr, errores
            )
            return jsonify({"ok": False, "error": " ".join(errores)}), 400
        # Validaciones adicionales que también están en el frontend:
        # Fecha válida
        if not validar_fecha_iso(str(datos.get("fecha", ""))):
            return jsonify({"ok": False, "error": "Fecha inválida. Usa formato YYYY-MM-DD"}), 400

        # Turno, WBS y zona son obligatorios en el formulario
        if not str(datos.get("turno", "")).strip():
            return jsonify({"ok": False, "error": "Falta el turno del despacho"}), 400
        if not str(datos.get("wbs", "")).strip():
            return jsonify({"ok": False, "error": "Falta el WBS del despacho"}), 400
        if not str(datos.get("zona", "")).strip():
            return jsonify({"ok": False, "error": "Falta la zona/destino del despacho"}), 400

        # Validar rangos opcionales (coinciden con atributos min/max en el HTML)
        try:
            if datos.get("arena_humedad_pct", "") not in ("", None):
                hum = _float_flexible(datos.get("arena_humedad_pct"))
                if hum < 4 or hum > 10:
                    return jsonify({"ok": False, "error": "arena_humedad_pct debe estar entre 4 y 10"}), 400
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "arena_humedad_pct no es un número válido"}), 400

        try:
            if datos.get("asentamiento_final_cm", "") not in ("", None):
                asent = _float_flexible(datos.get("asentamiento_final_cm"))
                if asent < 15 or asent > 30:
                    return jsonify({"ok": False, "error": "asentamiento_final_cm debe estar entre 15 y 30"}), 400
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "asentamiento_final_cm no es un número válido"}), 400

        try:
            if datos.get("temperatura_c", "") not in ("", None):
                temp = _float_flexible(datos.get("temperatura_c"))
                if temp < -10 or temp > 50:
                    return jsonify({"ok": False, "error": "temperatura_c debe estar entre -10 y 50"}), 400
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "temperatura_c no es un número válido"}), 400

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
            usuario_id=session.get("usuario_id"),
        )
        if not nuevo_id:
            return jsonify({"ok": False, "error": "No se pudo insertar el despacho."}), 400

        logger_seguridad.info(
            "Despacho creado | id=%s usuario=%s ip=%s",
            nuevo_id, session.get("username"), request.remote_addr
        )
        return jsonify({"ok": True, "id": nuevo_id})
    except Exception:
        logging.exception("Error en /api/despachos")
        return jsonify({"ok": False, "error": MSG_ERROR_GENERICO}), 500

# ===== API HISTORIAL =====

@app.route("/api/historial_consumo")
@admin_u_operador
def api_historial_consumo():
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
    except Exception:
        logging.exception("Error en /api/historial_consumo")
        return jsonify({"error": MSG_ERROR_GENERICO}), 500

# ===== API MATERIALES =====

@app.route("/api/materiales", methods=["GET", "POST"])
@admin_u_operador
def api_materiales():
    """Gestión de inventario de materiales.

    GET devuelve el inventario completo. POST crea un material nuevo si no
    recibe id, o actualiza el material existente cuando recibe id. Las acciones
    de creación/edición se mantienen restringidas al rol Admin.
    """
    if request.method == "GET":
        try:
            return jsonify({"ok": True, "materiales": obtener_materiales(ruta_bd=RUTA_BD)})
        except Exception:
            logging.exception("Error en GET /api/materiales")
            return jsonify({"ok": False, "error": MSG_ERROR_GENERICO}), 500

    if session.get("rol") != "Admin":
        logger_seguridad.warning(
            "Intento de edición de inventario sin rol Admin | usuario=%s rol=%s ip=%s",
            session.get("username"), session.get("rol"), request.remote_addr
        )
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
            # No permitir nombres que sean solo números
            if nombre.isdigit():
                return jsonify({"ok": False, "error": "El nombre del material no puede ser solo números"}), 400
            if not unidad:
                return jsonify({"ok": False, "error": "Falta la unidad del material"}), 400

            # Unidad permitida
            unidades_permitidas = {"kg", "l", "m3", "unidad"}
            if unidad not in unidades_permitidas:
                return jsonify({"ok": False, "error": "Unidad inválida"}), 400

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
                usuario_id=session.get("usuario_id"),
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
            usuario_id=session.get("usuario_id"),
        )
        if not actualizado:
            return jsonify({"ok": False, "error": "Material no encontrado"}), 404

        logger_seguridad.info(
            "Material actualizado | id=%s usuario=%s ip=%s datos=%s",
            material_id, session.get("username"), request.remote_addr, datos
        )
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
@admin_u_operador
def api_resumen_consumo():
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
        return jsonify({"ok": False, "error": MSG_ERROR_GENERICO}), 500

# ===== API ALERTAS CONSUMO =====

@app.route("/api/alertas_consumo")
@cualquier_usuario
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

# ===== API ZONAS =====

@app.route("/api/zonas")
@cualquier_usuario
def api_zonas():
    try:
        with conectar(RUTA_BD) as conexion:
            cursor = conexion.cursor()
            cursor.execute(
                "SELECT nombre_zona FROM Zonas ORDER BY nombre_zona"
            )
            zonas = [fila["nombre_zona"] for fila in cursor.fetchall()]
        return jsonify({"ok": True, "zonas": zonas})
    except Exception:
        logging.exception("Error en /api/zonas")
        return jsonify({"ok": False, "error": MSG_ERROR_GENERICO}), 500

# ===== API CRUCE CONSUMO VS STOCK =====

@app.route("/api/cruce_consumo_registro", methods=["POST"])
@admin_u_operador
def api_cruce_consumo_registro():
    try:
        datos = request.get_json(force=True)
        if not datos:
            return jsonify({"ok": False, "error": "No se recibieron datos"}), 400

        diseno = datos.get("diseno_mezcla")
        volumen_raw = datos.get("volumen_m3")
        fecha = datos.get("fecha")

        if not diseno or volumen_raw in (None, ""):
            return jsonify({"ok": False, "error": "Faltan diseno_mezcla o volumen"}), 400
        if not fecha or not validar_fecha_iso(str(fecha)):
            return jsonify({"ok": False, "error": "Falta o es inválida la fecha (YYYY-MM-DD)"}), 400

        try:
            volumen = _float_flexible(volumen_raw)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "El volumen_m3 no es un número válido"}), 400

        if volumen <= 0:
            return jsonify({"ok": False, "error": "El volumen_m3 debe ser mayor que 0"}), 400

        with conectar(RUTA_BD) as conexion:
            receta = _receta_por_diseno(conexion, diseno)
            if receta is None:
                return jsonify({"ok": False, "error": "No existe receta para el diseño indicado"}), 400
            consumos = _calcular_consumos_estimados(receta, volumen)

        salida, no_mapeados, no_encontrados = cruzar_consumo_vs_stock(consumos, ruta_bd=RUTA_BD)
        return jsonify({"ok": True, "datos": salida, "no_mapeados": no_mapeados, "no_encontrados": no_encontrados})
    except Exception:
        logging.exception("Error en /api/cruce_consumo_registro")
        return jsonify({"ok": False, "error": MSG_ERROR_GENERICO}), 500

# ===== API LOGIN =====
@app.route("/api/login", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def api_login():
    """
    Autentica al usuario y abre sesión.
    """
    datos = request.get_json(silent=True) or {}
    username = datos.get("usuario", "")
    password = datos.get("password", "")
    ip = get_remote_address()

    resultado = autenticar(username, password, ip=ip)

    if not resultado["ok"]:
        codigo = 423 if resultado.get("bloqueado") else 401
        return jsonify({"ok": False, "error": resultado["error"]}), codigo

    usuario = resultado["usuario"]
    session.clear()
    session["usuario_id"] = usuario["id"]
    session["username"] = usuario["username"]
    session["rol"] = usuario["rol"]
    session["ultima_actividad"] = time.time()

    return jsonify({"ok": True, "usuario": usuario})


# ===== LOGOUT =====
@app.route("/logout")
def logout():
    """Cierra la sesión y vuelve al login."""
    if "username" in session:
        logger_seguridad.info(
            "Logout | usuario=%s ip=%s", session.get("username"), request.remote_addr
        )
    session.clear()
    return redirect(url_for("login"))

# ===== INICIAR SERVIDOR =====

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")