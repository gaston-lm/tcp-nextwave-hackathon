from __future__ import annotations

from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from openai import OpenAIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .agent import TowerControlAgent
from .metrics import MetricsService
from .models import InvestigationRequest, InvestigationResponse
from .settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.pool = await asyncpg.create_pool(settings.resolved_database_url)
    app.state.engine = create_async_engine(
        settings.sqlalchemy_database_url,
        pool_pre_ping=True,
    )
    app.state.session_factory = async_sessionmaker(
        app.state.engine, expire_on_commit=False
    )
    yield
    await app.state.engine.dispose()
    await app.state.pool.close()


app = FastAPI(title="Control Tower Investigation API", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/investigations", response_model=InvestigationResponse)
async def investigate(
    payload: InvestigationRequest, request: Request
) -> InvestigationResponse:
    if get_settings().openai_api_key is None:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    metrics = MetricsService(
        request.app.state.pool,
        payload.as_of,
    )
    try:
        (
            detection,
            reviewer,
            persistence,
            actions,
            action_persistence,
        ) = await TowerControlAgent(
            metrics, request.app.state.session_factory
        ).investigate(payload.max_steps)
    except OpenAIError as error:
        raise HTTPException(
            status_code=502, detail=f"OpenAI investigation failed: {error}"
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error occurred: {error}"
        ) from error
    return InvestigationResponse(
        result=detection.result,
        steps_used=detection.steps_used,
        reviewer=reviewer,
        persistence={
            "created_incident_ids": persistence.created_incident_ids,
            "updated_incident_ids": persistence.updated_incident_ids,
        },
        action_taker=actions,
        action_persistence={
            "action_ids": action_persistence.action_ids,
            "action_types": action_persistence.action_types,
        },
    )
