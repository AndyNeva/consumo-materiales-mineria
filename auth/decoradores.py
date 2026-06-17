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