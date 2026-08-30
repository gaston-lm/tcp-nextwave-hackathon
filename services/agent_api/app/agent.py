"""Root orchestration boundary for the Control Tower agent workflow."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from .agents import AnomalyDetector, IncidentReviewer
from .incidents import IncidentRepository
from .metrics import MetricsService
from .models import IncidentReviewerResult, PaymentAnomalyDetectionResult
from .observability import traced_chain
from .persistence import IncidentWriter, PersistedIncidentChanges
from .settings import Settings


class TowerControlAgent:
    """Coordinate the staged incident workflow.

    Detection is followed by a read-only reviewer which proposes incident changes.
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
        PaymentAnomalyDetectionResult, IncidentReviewerResult, PersistedIncidentChanges
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
        return detection, review, persisted
