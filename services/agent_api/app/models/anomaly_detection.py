"""Strict structured-output contracts for Control Tower agents."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DimensionSignatures(StrictModel):
    merchant: str | None
    provider: str | None
    payment_method: str | None
    country: str | None
    issuing_bank: str | None


class AnomalyCluster(StrictModel):
    dimension_signatures: DimensionSignatures
    current_approval_rate: float = Field(ge=0, le=1)
    baseline_approval_rate: float | None = Field(ge=0, le=1)
    affected_attempts: int = Field(ge=0)
    excess_declines: float = Field(ge=0)
    evidence_tool_names: list[str] = Field(min_length=1)


class AnomalyInvestigation(StrictModel):
    investigation_status: Literal[
        "no_anomaly", "anomaly_detected", "insufficient_evidence"
    ]
    clusters: list[AnomalyCluster] = Field(max_length=10)
    unexplained_excess_declines_percent: float = Field(ge=0, le=100)
    summary: str = Field(min_length=1)


class PaymentAnomalyDetectionResult(StrictModel):
    result: AnomalyInvestigation
    steps_used: int = Field(ge=0)


class IncidentProposal(StrictModel):
    severity: Literal["urgent", "high", "medium", "low"]
    status: Literal["open", "closed", "needs_action"]
    title: str = Field(min_length=1)
    overview: str = Field(min_length=1)
    dimension_signatures: DimensionSignatures
    related_incident_ids: list[int]
    related_deployment_ids: list[str]
    match_rationale: str = Field(min_length=1)
    estimated_impact: float | None = Field(ge=0)
    approval_rate_drop: float | None = Field(ge=0, le=100)
    affected_transaction_count: int = Field(ge=0)
    started_at: datetime
    last_seen_at: datetime


class UpdatedIncidentProposal(IncidentProposal):
    incident_id: int = Field(gt=0)


class IncidentReviewDecision(StrictModel):
    new_incidents: list[IncidentProposal]
    updated_incidents: list[UpdatedIncidentProposal]


class IncidentReviewerResult(StrictModel):
    result: IncidentReviewDecision
    steps_used: int = Field(ge=0)


class ActionableIncident(StrictModel):
    incident_id: int = Field(gt=0)
    title: str
    overview: str
    dimension_signatures: DimensionSignatures
    related_deployment_ids: list[str]


class ActionProposal(StrictModel):
    incident_id: int = Field(gt=0)
    action_type: Literal[
        "deploy_rollback",
        "recommend_switch_provider_to_merchant",
        "post_slack_alert_to_channel",
    ]
    action_details: str = Field(min_length=1)


class ActionTakerResult(StrictModel):
    result: ActionProposal
    steps_used: int = Field(ge=0)


class RecentIncident(StrictModel):
    incident_id: int
    severity: Literal["urgent", "high", "medium", "low"]
    status: Literal["open", "closed", "needs_action"]
    title: str
    overview: str
    dimension_signatures: DimensionSignatures
    estimated_impact: float | None
    approval_rate_drop: float | None
    affected_transaction_count: int
    started_at: datetime
    last_seen_at: datetime
