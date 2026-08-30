"""SQLAlchemy read models used by IncidentReviewer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from .db_models import DeploymentLog, Incident, IncidentMemory
from .models import RecentIncident
from .observability import traced_tool


class IncidentRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def recent_open_incidents(self) -> list[RecentIncident]:
        statement = (
            select(Incident)
            .where(Incident.status == "open")
            .order_by(Incident.last_seen_at.desc())
        )
        async with self.session_factory() as session:
            incidents = list(await session.scalars(statement))
        return [
            RecentIncident(
                incident_id=item.incident_id,
                severity=item.severity,
                status=item.status,
                title=item.title,
                overview=item.overview,
                dimension_signatures=item.dimension_signatures,
                estimated_impact=item.estimated_impact,
                approval_rate_drop=item.approval_rate_drop,
                affected_transaction_count=item.affected_transaction_count,
                started_at=item.started_at,
                last_seen_at=item.last_seen_at,
            )
            for item in incidents
        ]

    @traced_tool(
        "search_closed_incidents",
        "Semantically searches closed incidents older than 24 hours.",
    )
    async def search_closed_incidents(
        self, embedding: list[float], limit: int = 5
    ) -> list[dict[str, Any]]:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        similarity = (1 - IncidentMemory.embedding.cosine_distance(embedding)).label(
            "similarity"
        )
        statement = (
            select(Incident, similarity)
            .join(IncidentMemory)
            .where(Incident.status == "closed", Incident.last_seen_at < cutoff)
            .order_by(IncidentMemory.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        async with self.session_factory() as session:
            rows = (await session.execute(statement)).all()
        return [
            {
                "incident_id": item.incident_id,
                "title": item.title,
                "overview": item.overview,
                "dimension_signatures": item.dimension_signatures,
                "status": item.status,
                "last_seen_at": item.last_seen_at,
                "similarity": similarity_score,
            }
            for item, similarity_score in rows
        ]

    @traced_tool(
        "search_recent_deploys",
        "Semantically searches payment processor deployment logs.",
    )
    async def search_deployments(
        self, embedding: list[float], limit: int = 5
    ) -> list[dict[str, Any]]:
        similarity = (1 - DeploymentLog.embedding.cosine_distance(embedding)).label(
            "similarity"
        )
        statement = (
            select(DeploymentLog, similarity)
            .order_by(DeploymentLog.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        async with self.session_factory() as session:
            rows = (await session.execute(statement)).all()
        return [
            {
                "deploy_id": item.deploy_id,
                "description_of_deploy": item.description_of_deploy,
                "dimensions_affected": item.dimensions_affected,
                "deployed_at": item.deployed_at,
                "similarity": similarity_score,
            }
            for item, similarity_score in rows
        ]
