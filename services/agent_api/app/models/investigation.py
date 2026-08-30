from datetime import datetime

from pydantic import BaseModel, Field

from .anomaly_detection import IncidentReviewerResult, PaymentAnomalyDetectionResult


class InvestigationRequest(BaseModel):
    as_of: datetime | None = None
    max_steps: int = Field(default=12, ge=1, le=20)


class IncidentPersistence(BaseModel):
    created_incident_ids: list[int]
    updated_incident_ids: list[int]


class InvestigationResponse(PaymentAnomalyDetectionResult):
    reviewer: IncidentReviewerResult
    persistence: IncidentPersistence
