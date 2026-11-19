FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY libs/minehub_common /libs/minehub_common
RUN pip install --no-cache-dir /libs/minehub_common \
        "dagster>=1.7" "dagster-webserver>=1.7" "dagster-postgres>=0.23" "dagster-dbt>=0.23" \
        "dbt-core>=1.8" "dbt-postgres>=1.8" \
        "pandas>=2.2" "openpyxl>=3.1" \
        "psycopg[binary]>=3.1" "redis>=5.0" "pyyaml>=6.0" \
        "pydantic>=2.7" "pydantic-settings>=2.2" "sqlalchemy>=2.0" \
        "jinja2>=3.1" "weasyprint>=62" "matplotlib>=3.8"

COPY orchestration /app/orchestration
COPY warehouse /app/warehouse
COPY reporting /app/reporting
COPY config /app/config
COPY libs /app/libs
COPY schemas /app/schemas
COPY simulators /app/simulators
COPY pyproject.toml README.md /app/
RUN pip install --no-cache-dir --no-deps /app alembic confluent-kafka fastavro httpx

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DAGSTER_HOME=/opt/dagster/dagster_home
ENV CONFIG_DIR=/app/config
ENV SCHEMA_DIR=/app/schemas
RUN mkdir -p /opt/dagster/dagster_home \
    && cp /app/orchestration/dagster.yaml /opt/dagster/dagster_home/dagster.yaml
WORKDIR /app

CMD ["dagster-webserver", "-w", "/app/orchestration/workspace.yaml", "-h", "0.0.0.0", "-p", "3000"]
