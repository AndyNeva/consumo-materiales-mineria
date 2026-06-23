"""
Paquete de autenticación y control de acceso por roles.

Responsable: Juan Ruiz (@eljuandaruiz).

Exporta lo esencial para que app.py importe corto:

    from auth import autenticar, rol_requerido, solo_admin, login_required
"""

from auth.login import autenticar, esta_bloqueado, hashear_password
from auth.roles import (
    rol_requerido,
    solo_admin,
    admin_u_operador,
    cualquier_usuario,
    ROLES_VALIDOS,
)

__all__ = [
    "autenticar",
    "esta_bloqueado",
    "hashear_password",
    "rol_requerido",
    "solo_admin",
    "admin_u_operador",
    "cualquier_usuario",
    "ROLES_VALIDOS",
    "login_required",
]
