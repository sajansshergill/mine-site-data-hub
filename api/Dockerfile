FROM python:3.11-slim

WORKDIR /app

COPY libs/minehub_common /libs/minehub_common
RUN pip install --no-cache-dir /libs/minehub_common \
    fastapi "uvicorn[standard]" sqlalchemy redis prometheus-client lupa pyyaml psycopg[binary]

COPY api/app /app/app
COPY libs /app/libs
COPY config /app/config
COPY kpi_engine /app/kpi_engine

ENV PYTHONPATH=/app
ENV CONFIG_DIR=/app/config
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
