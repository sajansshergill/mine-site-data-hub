"""COPY-based bulk insert and upsert helpers (psycopg3)."""
from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from typing import Any

import psycopg


def _as_csv(rows: Iterable[Sequence[Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    return buf.getvalue()


def copy_rows(conn: psycopg.Connection, table: str, columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> int:
    if not rows:
        return 0
    cols = ", ".join(columns)
    with conn.cursor() as cur:
        with cur.copy(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv)") as copy:
            copy.write(_as_csv(rows))
    return len(rows)


def upsert_via_staging(
    conn: psycopg.Connection,
    table: str,
    columns: Sequence[str],
    key_columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> int:
    """Load into a temp staging table then upsert into the target."""
    if not rows:
        return 0
    cols = ", ".join(columns)
    keys = ", ".join(key_columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c not in key_columns)
    staging = f"_stg_{table.replace('.', '_')}"
    with conn.cursor() as cur:
        cur.execute(f"CREATE TEMP TABLE {staging} (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP")
        with cur.copy(f"COPY {staging} ({cols}) FROM STDIN WITH (FORMAT csv)") as copy:
            copy.write(_as_csv(rows))
        if updates:
            cur.execute(
                f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {staging} "
                f"ON CONFLICT ({keys}) DO UPDATE SET {updates}"
            )
        else:
            cur.execute(
                f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {staging} ON CONFLICT ({keys}) DO NOTHING"
            )
    return len(rows)
