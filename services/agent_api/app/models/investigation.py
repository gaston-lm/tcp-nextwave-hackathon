from datetime import datetime

from pydantic import BaseModel, Field

from .anomaly_detection import (
    ActionTakerResult,
    IncidentReviewerResult,
    PaymentAnomalyDetectionResult,
)


class InvestigationRequest(BaseModel):
    """``as_of`` is the observation timestamp; naive values are interpreted as UTC."""

    as_of: datetime | None = None
    max_steps: int = Field(default=12, ge=1, le=20)


class IncidentPersistence(BaseModel):
    created_incident_ids: list[int]
    updated_incident_ids: list[int]


class ActionPersistence(BaseModel):
    action_ids: list[int]
    action_types: list[str]


class InvestigationResponse(PaymentAnomalyDetectionResult):
    reviewer: IncidentReviewerResult
    persistence: IncidentPersistence
    action_taker: list[ActionTakerResult]
    action_persistence: ActionPersistence
