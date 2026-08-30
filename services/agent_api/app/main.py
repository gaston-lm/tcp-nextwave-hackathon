from __future__ import annotations

from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from openai import OpenAIError

from .metrics import MetricsService
from .models import InvestigationRequest, InvestigationResponse
from .agent import TowerControlAgent
from .settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(get_settings().resolved_database_url)
    yield
    await app.state.pool.close()


app = FastAPI(title="Control Tower Investigation API", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/investigations", response_model=InvestigationResponse)
async def investigate(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    if get_settings().openai_api_key is None:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    metrics = MetricsService(
        request.app.state.pool,
        payload.as_of,
    )
    try:
        detection = await TowerControlAgent(metrics).investigate(payload.max_steps)
    except OpenAIError as error:
        raise HTTPException(status_code=502, detail=f"OpenAI investigation failed: {error}") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {error}") from error
    return InvestigationResponse(result=detection.result, steps_used=detection.steps_used)
