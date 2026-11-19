"""Shared helpers for Dagster batch load assets."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

import psycopg
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def latest(drop_dir: Path, pattern: str) -> Path | None:
    drop_dir.mkdir(parents=True, exist_ok=True)
    matches = sorted(drop_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def validate_rows(records: list[dict[str, Any]], model: type[T]) -> tuple[list[T], list[dict[str, Any]]]:
    good: list[T] = []
    bad: list[dict[str, Any]] = []
    for rec in records:
        try:
            good.append(model.model_validate(rec))
        except ValidationError as exc:
            bad.append({"record": rec, "errors": exc.errors()})
    return good, bad


def quarantine(conn: psycopg.Connection, source: str, bad: list[dict[str, Any]]) -> None:
    if not bad:
        return
    with conn.cursor() as cur:
        for item in bad:
            cur.execute(
                "INSERT INTO ops.quarantine (source, reason, payload) VALUES (%s, %s, %s::jsonb)",
                (source, "validation_error", json.dumps(item, default=str)),
            )


def archive(path: Path) -> Path:
    archive_dir = path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = archive_dir / f"{path.stem}_{stamp}{path.suffix}"
    shutil.move(str(path), str(dest))
    return dest
