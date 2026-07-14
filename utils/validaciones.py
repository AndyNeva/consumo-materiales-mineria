"""
Validación de cédula ecuatoriana.

Algoritmo de módulo 10 usado por el Registro Civil,más una capa de bloqueo 
de patrones triviales (dígitos repetidos,secuencias obvias) que el checksum 
por sí solo no detecta: números como "2222222222" son matemáticamente válidos 
para el algoritmo de módulo 10pero no corresponden a ninguna cédula real emitida.
"""

from __future__ import annotations

import re

_COEFICIENTES_CI = (2, 1, 2, 1, 2, 1, 2, 1, 2)
_NUM_PROVINCIAS = 24
_TERCER_DIGITO_MAX = 6  # tercer dígito > 6 no corresponde a persona natural

_PATRONES_TRIVIALES = (
    re.compile(r"^(\d)\1{9}$"),   # 0000000000 ... 9999999999
    re.compile(r"^0123456789$"),
    re.compile(r"^1234567890$"),
)


def _es_patron_trivial(cedula: str) -> bool:
    """Detecta secuencias que pasan el checksum pero nunca son reales."""
    return any(patron.match(cedula) for patron in _PATRONES_TRIVIALES)


def _validar_checksum_ci(cedula: str) -> bool:
    """Algoritmo de módulo 10 del Registro Civil ecuatoriano."""
    tercer_digito = int(cedula[2])
    if tercer_digito > _TERCER_DIGITO_MAX:
        return False

    codigo_provincia = int(cedula[0:2])
    if codigo_provincia < 1 or codigo_provincia > _NUM_PROVINCIAS:
        return False

    verificador_recibido = int(cedula[9])
    suma = 0
    for coef, digito in zip(_COEFICIENTES_CI, cedula[:9]):
        valor = coef * int(digito)
        suma += valor - 9 if valor > 9 else valor

    residuo = suma % 10
    verificador_obtenido = 10 - residuo if residuo != 0 else 0

    return verificador_obtenido == verificador_recibido


def validar_cedula(cedula: str) -> bool:
    """
    Valida una cédula ecuatoriana.

    Aplica, en orden:
      1. Formato: exactamente 10 dígitos numéricos.
      2. Bloqueo de patrones triviales (repetidos, secuenciales).
      3. Checksum módulo 10.

    Args:
        cedula (str): Número de cédula a validar.

    Returns:
        bool: True si pasa las tres validaciones.
    """
    cedula = (cedula or "").strip()

    if not re.fullmatch(r"\d{10}", cedula):
        return False

    if _es_patron_trivial(cedula):
        return False

    return _validar_checksum_ci(cedula)