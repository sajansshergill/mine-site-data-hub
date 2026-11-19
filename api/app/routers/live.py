"""Live shift state from Redis, including SSE stream."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import require
from app.deps import redis_client
from app.schemas.models import LiveShift
from app.services.live_state import read_live

router = APIRouter(tags=["live"])


@router.get("/live/shift", response_model=LiveShift)
def live_shift(_: str = Depends(require("viewer"))) -> LiveShift:
    return read_live(redis_client())


@router.get("/live/stream")
async def live_stream(_: str = Depends(require("viewer"))) -> StreamingResponse:
    async def events():  # noqa: ANN202
        r = redis_client()
        while True:
            state = read_live(r)
            yield f"data: {json.dumps(state.model_dump())}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(events(), media_type="text/event-stream")
