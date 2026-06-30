"""
Configuración centralizada de logging de seguridad.

Separa los eventos de seguridad (logins, accesos denegados, cambios
sensibles) en su propio archivo, distinto del log general de errores
de la aplicación.
"""

import logging

def configurar_logging():
    """Configura handlers de archivo y consola para toda la app."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("seguridad.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

# Logger específico para eventos de seguridad (login, accesos, roles)
logger_seguridad = logging.getLogger("seguridad")