from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlantTag(BaseModel):
    tag: str
    ts: datetime
    value: float
    source: str = "opcua"
    quality: Literal["GOOD", "UNCERTAIN", "BAD"] = "GOOD"

    def to_avro(self) -> dict[str, Any]:
        return {
            "ts": int(self.ts.timestamp() * 1000),
            "tag": self.tag,
            "source": self.source,
            "value": float(self.value),
            "quality": self.quality,
        }
