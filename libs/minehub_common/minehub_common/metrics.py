"""Shared Prometheus metrics used by connectors and processors."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

MESSAGES_IN = Counter("minehub_messages_in_total", "Messages received", ["service", "source"])
MESSAGES_OUT = Counter("minehub_messages_out_total", "Messages published", ["service", "topic"])
VALIDATION_FAIL = Counter("minehub_validation_failures_total", "Contract validation failures", ["service", "reason"])
RECONNECTS = Counter("minehub_reconnects_total", "Protocol reconnects", ["service", "target"])
LAST_MESSAGE_TS = Gauge("minehub_last_message_unixtime", "Unix time of last message", ["service", "source"])
PROCESS_SECONDS = Histogram("minehub_process_seconds", "Processing latency", ["service", "stage"])
DLQ_TOTAL = Counter("minehub_dlq_total", "Dead-letter messages", ["service", "topic"])


def start_metrics_server(port: int) -> None:
    start_http_server(port)
