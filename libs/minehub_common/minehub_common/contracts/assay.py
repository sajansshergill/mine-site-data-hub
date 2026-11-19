from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class Assay(BaseModel):
    sample_id: str
    location: str
    block_id: str
    sampled_on: date
    au_gpt: float = Field(ge=0)
    tonnes_represented: float = Field(gt=0)
