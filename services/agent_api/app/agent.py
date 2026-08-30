"""Root orchestration boundary for the Control Tower agent workflow."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from .agents import ActionTaker, AnomalyDetector, IncidentReviewer
from .incidents import IncidentRepository
from .metrics import MetricsService
from .models import (
    ActionTakerResult,
    IncidentReviewerResult,
    PaymentAnomalyDetectionResult,
)
from .observability import traced_chain
from .persistence import (
    IncidentActionWriter,
    IncidentWriter,
    PersistedActions,
    PersistedIncidentChanges,
)
from .settings import Settings


class TowerControlAgent:
    """Coordinate the staged incident workflow.

    Detection is followed by read-only review and action-planning stages.
    """

    def __init__(
        self,
        metrics: MetricsService,
        session_factory: async_sessionmaker,
        settings: Settings | None = None,
    ) -> None:
        self.metrics = metrics
        self.session_factory = session_factory
        self.settings = settings

    @traced_chain("tower_control_agent")
    async def investigate(
        self, max_steps: int
    ) -> tuple[
        PaymentAnomalyDetectionResult,
        IncidentReviewerResult,
        PersistedIncidentChanges,
        list[ActionTakerResult],
        PersistedActions,
    ]:
        detection = await AnomalyDetector(
            self.metrics,
            settings=self.settings,
        ).detect(max_steps)
        repository = IncidentRepository(self.session_factory)
        recent_incidents = await repository.recent_open_incidents()
        review = await IncidentReviewer(repository, settings=self.settings).review(
            detection.result, recent_incidents, max_steps
        )
        persisted = await IncidentWriter(self.session_factory).apply(review.result)
        new_incidents = await repository.new_incidents(persisted.created_incident_ids)
        actions: list[ActionTakerResult] = []
        if new_incidents:
            action_taker = ActionTaker(repository, settings=self.settings)
            actions = [
                await action_taker.decide(incident, max_steps)
                for incident in new_incidents
            ]
        action_persistence = await IncidentActionWriter(self.session_factory).apply(
            [item.result for item in actions]
        )
        return detection, review, persisted, actions, action_persistence
