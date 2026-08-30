"""Root orchestration boundary for the Control Tower agent workflow."""

from __future__ import annotations

from .agents.anomaly_detector import AnomalyDetector
from .models import PaymentAnomalyDetectionResult
from .metrics import MetricsService
from .observability import traced_agent
from .settings import Settings


class TowerControlAgent:
    """Coordinate the staged incident workflow.

    Only anomaly detection is active today. Incident-novelty analysis and action-item
    creation will become later stages under this same root agent boundary.
    """

    def __init__(self, metrics: MetricsService, settings: Settings | None = None) -> None:
        self.metrics = metrics
        self.settings = settings

    @traced_agent("tower_control_agent")
    async def investigate(self, max_steps: int) -> PaymentAnomalyDetectionResult:
        return await AnomalyDetector(
            self.metrics,
            settings=self.settings,
        ).detect(max_steps)
