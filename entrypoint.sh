#!/bin/sh
set -e

# Ruta de la BD: usa DB_PATH si está definida (debe apuntar al volumen
# persistente montado en Railway, ej. /data/gestion_materiales.db).
# Si no está definida, cae al valor por defecto de utils/db.py.
DB_FILE="${DB_PATH:-/app/db/gestion_materiales.db}"
DB_DIR="$(dirname "$DB_FILE")"

mkdir -p "$DB_DIR"

if [ ! -f "$DB_FILE" ]; then
    echo "[entrypoint] No existe la base de datos en $DB_FILE."
    echo "[entrypoint] Creando esquema inicial..."
    python db/01_crear_esquema.py

    echo "[entrypoint] Poblando insumos base y usuarios demo..."
    python db/02_poblar_insumos.py

    echo "[entrypoint] Seed inicial completado."
else
    echo "[entrypoint] Base de datos existente encontrada en $DB_FILE. Se omite el seed."
fi

echo "[entrypoint] Iniciando gunicorn en el puerto ${PORT:-8080}..."
exec gunicorn app:app \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers 2 \
    --threads 4 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
