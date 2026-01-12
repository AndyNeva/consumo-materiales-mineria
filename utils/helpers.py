from datetime import timedelta, date

def ultimos_7_dias():
    """
    Retorna una lista de 7 strings con las fechas desde hoy
    hasta hace 6 días atrás (hoy incluido), en formato 'YYYY-MM-DD'.
    Ejemplo: ['2026-01-07', '2026-01-06', ..., '2026-01-01']
    """
    hoy = date.today()
    fechas = []
    for i in range(7):
        dia = hoy - timedelta(days=i)
        fechas.append(dia.isoformat())  # Convierte a 'YYYY-MM-DD'
    return fechas

def mapeo_materiales():
    mapeo = {
        "cemento_kg": "Cemento",
        "grava_kg": "Grava",
        "arena_kg": "Arena",
        "agua_kg": "Agua",
        "aditivo_rheo_sika115" : ["RHEO 1000 (kg)", "Sika 115 (kg)"],
        "aditivo_basf_sika200" : ["BASF 719 (kg)", "Sika 200 (kg)"],
        "aditivo_delvo": "Delvo",
        "aditivo_glenium_7950": "MasterGlenium 7950",
        "aditivo_glenium_7970": "MasterGlenium 7970",
        "aditivo_fibras": "Sika PP 48 - BARCHIP"
    }
    return mapeo
