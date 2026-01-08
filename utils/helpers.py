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
