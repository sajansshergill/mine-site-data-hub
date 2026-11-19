FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY libs/minehub_common /libs/minehub_common
RUN pip install --no-cache-dir /libs/minehub_common \
    jinja2 weasyprint matplotlib pandas sqlalchemy psycopg[binary] pyyaml

COPY reporting /app/reporting
COPY config /app/config
COPY libs /app/libs

ENV PYTHONPATH=/app
ENV CONFIG_DIR=/app/config
ENV REPORT_DIR=/app/reporting/output
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "reporting.shift_report", "--shift", "latest"]
