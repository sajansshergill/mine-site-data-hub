FROM python:3.11-slim
WORKDIR /app

COPY libs/minehub_common /libs/minehub_common
RUN pip install --no-cache-dir /libs/minehub_common \
    paho-mqtt \
    asyncua \
    pymodbus \
    python-dateutil \
    confluent-kafka \
    fastavro \
    prometheus-client \
    pyyaml \
    pydantic \
    pydantic-settings \
    tenacity

COPY connectors /app/connectors
COPY config /app/config
COPY schemas /app/schemas

ENV CONFIG_DIR=/app/config \
    SCHEMA_DIR=/app/schemas \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

CMD ["python", "-m", "connectors.mqtt_connector.main"]
