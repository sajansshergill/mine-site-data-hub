"""Mine Site Data Hub API."""
from __future__ import annotations

import time

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, make_asgi_app

from app.routers import data_quality, equipment, health, kpis, live, maintenance, shifts
from minehub_common.logging import setup_logging

setup_logging("api")

REQUESTS = Counter("minehub_api_requests_total", "API requests", ["method", "route", "status"])
LATENCY = Histogram("minehub_api_request_seconds", "API latency", ["route"])

app = FastAPI(title="Mine Site Data Hub API", version="0.1.0",
              description="Plan vs actual, live shift state, equipment KPIs and data quality for the site.")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):  # noqa: ANN001, ANN201
    started = time.perf_counter()
    response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", request.url.path)
    REQUESTS.labels(request.method, route, response.status_code).inc()
    LATENCY.labels(route).observe(time.perf_counter() - started)
    return response


for r in (health, shifts, live, equipment, maintenance, kpis, data_quality):
    app.include_router(r.router)
app.mount("/metrics", make_asgi_app())