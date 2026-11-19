FROM python:3.11-slim
WORKDIR /app

COPY libs/minehub_common /libs/minehub_common
RUN pip install --no-cache-dir /libs/minehub_common \
    networkx \
    asyncua \
    "pymodbus>=3.6,<3.8" \
    paho-mqtt \
    openpyxl \
    pyyaml

COPY simulators /app/simulators
COPY config /app/config
COPY schemas /app/schemas

ENV CONFIG_DIR=/app/config \
    SCHEMA_DIR=/app/schemas \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

CMD ["python", "-m", "simulators.fleet.main"]
