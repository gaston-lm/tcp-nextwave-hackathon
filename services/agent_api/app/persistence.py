"""Deterministic incident writer run after the reviewer, outside the agent loop."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from .db_models import Incident
from .models import IncidentProposal, IncidentReviewDecision


@dataclass(frozen=True)
class PersistedIncidentChanges:
    created_incident_ids: list[int]
    updated_incident_ids: list[int]


class IncidentWriter:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def apply(self, decision: IncidentReviewDecision) -> PersistedIncidentChanges:
        async with self.session_factory.begin() as session:
            created = [self._new_incident(item) for item in decision.new_incidents]
            session.add_all(created)
            update_ids = [item.incident_id for item in decision.updated_incidents]
            existing = {
                item.incident_id: item
                for item in await session.scalars(
                    select(Incident).where(Incident.incident_id.in_(update_ids))
                )
            }
            missing = set(update_ids) - existing.keys()
            if missing:
                raise ValueError(f"Cannot update missing incidents: {sorted(missing)}")
            for proposal in decision.updated_incidents:
                self._assign(existing[proposal.incident_id], proposal)
            await session.flush()
            return PersistedIncidentChanges(
                created_incident_ids=[item.incident_id for item in created],
                updated_incident_ids=update_ids,
            )

    @staticmethod
    def _new_incident(proposal: IncidentProposal) -> Incident:
        incident = Incident()
        IncidentWriter._assign(incident, proposal)
        return incident

    @staticmethod
    def _assign(incident: Incident, proposal: IncidentProposal) -> None:
        incident.severity = proposal.severity
        incident.status = proposal.status
        incident.title = proposal.title
        incident.overview = proposal.overview
        incident.dimension_signatures = proposal.dimension_signatures.model_dump(
            exclude_none=True
        )
        incident.related_incidents = proposal.related_incident_ids
        incident.related_deployments = proposal.related_deployment_ids
        incident.estimated_impact = proposal.estimated_impact
        incident.approval_rate_drop = proposal.approval_rate_drop
        incident.affected_transaction_count = proposal.affected_transaction_count
        incident.started_at = proposal.started_at
        incident.last_seen_at = proposal.last_seen_at
