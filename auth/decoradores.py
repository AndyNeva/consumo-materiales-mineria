from functools import wraps
from flask import session, request, redirect, url_for, jsonify

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "usuario_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "No autenticado"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# Control de acceso por rol (Juan Ruiz @eljuandaruiz).
# login_required solo verifica que haya sesión. Para restringir por rol,
# usa los decoradores de auth/roles.py (rol_requerido, solo_admin, ...),
# que leen session["rol"] guardado al iniciar sesión.
# Se reexportan aquí para que el código existente pueda importarlos desde
# auth.decoradores sin romper nada.
from auth.roles import rol_requerido, solo_admin, admin_u_operador, cualquier_usuario  # noqa: E402,F401