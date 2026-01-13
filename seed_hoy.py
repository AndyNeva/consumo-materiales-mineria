from datetime import date
from utils.loaders import insertar_despacho

hoy = date.today().isoformat()

print("Insertando despacho de prueba con fecha:", hoy)

despacho_id = insertar_despacho(
    fecha=hoy,
    volumen=10.5,               # volumen_m3
    diseno_mezcla="H-25",        # OJO: debe existir en la tabla recetas
    wbs="WBS-TEST",
    destino="FDN",
    humedad_arena=5,
    asentamiento_final=12,
    temperatura=24
)

print("ID insertado:", despacho_id)
