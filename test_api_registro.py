"""
Script de prueba para la API de registro de despachos.
Este script envía una petición POST a la API /api/registro
"""

import requests
import json

# URL de la API (ajustar si el servidor corre en otro puerto)
url = "http://127.0.0.1:5000/api/registro"

# Datos de ejemplo para un nuevo despacho
datos_despacho = {
    "fecha": "2026-01-12",
    "volumen": 5.0,
    "diseno_mezcla": "H-210-45-19-G",
    "wbs": "WBS-001",
    "destino": "Zona Norte",
    "turno": "Matutino",
    "humedad_arena": 3.5,
    "asentamiento_final": 18.0,
    "temperatura": 25.0,
    "usuario_id": 1
}

# Realizar la petición POST
try:
    response = requests.post(
        url,
        json=datos_despacho,
        headers={"Content-Type": "application/json"}
    )
    
    # Mostrar resultado
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
except requests.exceptions.ConnectionError:
    print("❌ Error: No se pudo conectar al servidor. Asegúrate de que Flask esté corriendo.")
except Exception as e:
    print(f"❌ Error inesperado: {e}")
