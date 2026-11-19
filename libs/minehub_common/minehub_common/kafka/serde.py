"""Avro (de)serialization via Redpanda Schema Registry (Confluent wire format)."""
from __future__ import annotations

import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

import fastavro
import httpx


class AvroSerde:
    def __init__(self, registry_url: str, schema_dir: Path | None = None) -> None:
        self.registry_url = registry_url.rstrip("/")
        self.schema_dir = schema_dir
        self._id_cache: dict[str, int] = {}
        self._schema_cache: dict[int, dict[str, Any]] = {}

    def register(self, subject: str, schema: dict[str, Any]) -> int:
        resp = httpx.post(
            f"{self.registry_url}/subjects/{subject}/versions",
            json={"schema": __import__("json").dumps(schema)},
            timeout=10,
        )
        resp.raise_for_status()
        schema_id = int(resp.json()["id"])
        self._id_cache[subject] = schema_id
        self._schema_cache[schema_id] = schema
        return schema_id

    def schema_id(self, subject: str) -> int:
        if subject in self._id_cache:
            return self._id_cache[subject]
        resp = httpx.get(f"{self.registry_url}/subjects/{subject}/versions/latest", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        schema_id = int(data["id"])
        self._id_cache[subject] = schema_id
        self._schema_cache[schema_id] = __import__("json").loads(data["schema"])
        return schema_id

    def encode(self, subject: str, record: dict[str, Any], schema: dict[str, Any] | None = None) -> bytes:
        schema_id = self._id_cache.get(subject)
        if schema_id is None:
            if schema is None and self.schema_dir:
                raise ValueError(f"schema for {subject} not registered and none provided")
            schema_id = self.register(subject, schema) if schema else self.schema_id(subject)
        parsed = fastavro.parse_schema(schema or self._schema_cache[schema_id])
        buf = __import__("io").BytesIO()
        buf.write(b"\x00")
        buf.write(struct.pack(">I", schema_id))
        fastavro.schemaless_writer(buf, parsed, record)
        return buf.getvalue()

    def decode(self, payload: bytes) -> dict[str, Any]:
        if payload[0:1] != b"\x00":
            raise ValueError("not Confluent Avro wire format")
        schema_id = struct.unpack(">I", payload[1:5])[0]
        schema = self._fetch_schema(schema_id)
        parsed = fastavro.parse_schema(schema)
        return fastavro.schemaless_reader(__import__("io").BytesIO(payload[5:]), parsed)

    def _fetch_schema(self, schema_id: int) -> dict[str, Any]:
        if schema_id in self._schema_cache:
            return self._schema_cache[schema_id]
        resp = httpx.get(f"{self.registry_url}/schemas/ids/{schema_id}", timeout=10)
        resp.raise_for_status()
        schema = __import__("json").loads(resp.json()["schema"])
        self._schema_cache[schema_id] = schema
        return schema


@lru_cache
def load_schema(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
