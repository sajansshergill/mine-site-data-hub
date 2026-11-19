from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class PlanRow(BaseModel):
    shift_date: date
    shift_code: str = Field(pattern="^[DN]$")
    location: str
    material: str
    planned_tonnes: float = Field(ge=0)
    planned_grade_gpt: float | None = Field(default=None, ge=0)
    planned_truck_hours: float | None = Field(default=None, ge=0)
    plan_version: str
    shift_id: str = ""

    @model_validator(mode="after")
    def build_shift_id(self) -> PlanRow:
        if not self.shift_id:
            self.shift_id = f"{self.shift_date.isoformat()}-{self.shift_code}"
        material = self.material.upper()
        if material not in {"ORE", "WASTE"}:
            raise ValueError(f"material must be ORE or WASTE, got {self.material}")
        self.material = material
        return self
