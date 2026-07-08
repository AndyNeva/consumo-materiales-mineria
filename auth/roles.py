"""
Decoradores para proteger rutas según el rol del usuario.

Los 3 perfiles del sistema:

  - Admin        : acceso total (ver, agregar, editar, eliminar, gestionar usuarios).
  - Operador     : puede ver inventario y agregar registros (con validación previa).
  - Visualizador : solo puede ver el dashboard principal.

Uso típico en app.py:

    from auth.roles import rol_requerido, solo_admin

    @app.route("/inventario")
    @rol_requerido("Admin", "Operador")
    def inventario():
        ...

    @app.route("/usuarios")
    @solo_admin
    def usuarios():
        ...

Nota: rol_requerido ya verifica que el usuario haya iniciado sesión, así que
no hace falta combinarlo con login_required.
"""

from __future__ import annotations

from functools import wraps
from flask import session, request, redirect, url_for, jsonify
from utils.logging_seguridad import logger_seguridad

# Roles válidos (debe coincidir con auth/login.py).
ROLES_VALIDOS = ("Admin", "Operador", "Visualizador")


def _no_autenticado_response():
    logger_seguridad.warning(
        "Acceso sin sesión | ruta=%s ip=%s", request.path, request.remote_addr
    )
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "No autenticado"}), 401
    return redirect(url_for("login"))


def _sin_permiso_response():
    logger_seguridad.warning(
        "Acceso denegado por rol | usuario=%s rol=%s ruta=%s ip=%s",
        session.get("username"), session.get("rol"), request.path, request.remote_addr
    )
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "No tienes permiso para esta acción"}), 403
    return redirect(url_for("dashboard"))


def rol_requerido(*roles_permitidos: str):
    def decorador(f):
        @wraps(f)
        def envoltura(*args, **kwargs):
            if "usuario_id" not in session:
                return _no_autenticado_response()

            if session.get("rol") not in roles_permitidos:
                return _sin_permiso_response()

            return f(*args, **kwargs)
        return envoltura
    return decorador


def solo_admin(f):
    return rol_requerido("Admin")(f)


def admin_u_operador(f):
    return rol_requerido("Admin", "Operador")(f)


def cualquier_usuario(f):
    return rol_requerido(*ROLES_VALIDOS)(f)
