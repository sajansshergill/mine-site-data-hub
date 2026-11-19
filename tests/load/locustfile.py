"""Load test: health + live shift endpoints under concurrent dashboard users."""
from __future__ import annotations

import os

from locust import HttpUser, between, task

API_KEY = os.environ.get("LOCUST_API_KEY", "viewer-key")


class DashboardUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        self.client.headers.update({"X-API-Key": API_KEY})

    @task(3)
    def health(self) -> None:
        self.client.get("/health")

    @task(5)
    def live_shift(self) -> None:
        self.client.get("/live/shift")
