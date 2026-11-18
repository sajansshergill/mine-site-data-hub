FROM python:3.11-slim
WORKDIR /app
COPY libs/minehub_common /libs/minehub_common
RUN pip install --no-cache-dir /libs/minehub_common paho-mqtt asyncua pymodbus
COPY connectors /app/connectors
COPY config /app/config
COPY schemas /app/schemas
ENV CONFIG_DIR=/app/config SCHEMA_DIR=/app/schemas PYTHONUNBUFFERED=1
CMD ["python", "-m", "connectors.mqtt_connector.main"]