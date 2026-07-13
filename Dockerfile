# Dockerfile — Planta de Hormigón (Flask + SQLite)
# Pensado para Railway: usa gunicorn, respeta $PORT dinámico y
# hace seed de la base de datos solo si no existe (ver entrypoint.sh).

FROM python:3.11-slim

# Evita .pyc y fuerza logs sin buffer (útil para ver logs en Railway al instante)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema mínimas para compilar wheels si hiciera falta
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias Python primero (cachea mejor entre builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Entrypoint: hace seed de la BD si no existe y luego levanta gunicorn
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Railway inyecta $PORT en runtime; se documenta 8080 solo como referencia local
EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
