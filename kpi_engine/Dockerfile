FROM python:3.11-slim

WORKDIR /app

COPY libs/minehub_common /libs/minehub_common
RUN pip install --no-cache-dir /libs/minehub_common \
    lupa pyyaml sqlalchemy psycopg[binary]

COPY kpi_engine /app/kpi_engine
COPY config /app/config
COPY libs /app/libs

ENV PYTHONPATH=/app
ENV CONFIG_DIR=/app/config
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "kpi_engine.engine", "--shift", "latest"]
