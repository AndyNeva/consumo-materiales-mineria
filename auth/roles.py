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

# Roles válidos (debe coincidir con auth/login.py).
ROLES_VALIDOS = ("Admin", "Operador", "Visualizador")


def _no_autenticado_response():
    """Respuesta cuando no hay sesión iniciada."""
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "No autenticado"}), 401
    return redirect(url_for("login"))


def _sin_permiso_response():
    """Respuesta cuando el usuario está logueado pero su rol no alcanza."""
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "No tienes permiso para esta acción"}), 403
    # 403 con la página de dashboard básica como destino seguro.
    return redirect(url_for("dashboard"))


def rol_requerido(*roles_permitidos: str):
    """
    Restringe una ruta a uno o más roles.

    Ejemplo:
        @rol_requerido("Admin", "Operador")
        def vista(): ...
    """
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


# Atajos para los casos más comunes ----------------------------------------

def solo_admin(f):
    """Solo el Administrador puede entrar."""
    return rol_requerido("Admin")(f)


def admin_u_operador(f):
    """Admin u Operador (ver inventario, agregar registros)."""
    return rol_requerido("Admin", "Operador")(f)


def cualquier_usuario(f):
    """Cualquier rol válido autenticado (incluye Visualizador)."""
    return rol_requerido(*ROLES_VALIDOS)(f)
