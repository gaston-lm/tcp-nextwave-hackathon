from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from services.agent_api.app.models.anomaly_detection import (
    AnomalyInvestigation,
    DimensionSignatures,
    IncidentReviewDecision,
    UpdatedIncidentProposal,
)
from services.agent_api.app.structured_output import parse_output, response_format


def signatures(**overrides):
    return {
        "merchant": None,
        "provider": "Acquirer A",
        "payment_method": None,
        "country": "Argentina",
        "issuing_bank": None,
        **overrides,
    }


def proposal(**overrides):
    return {
        "severity": "high",
        "status": "open",
        "title": "Acquirer authorization decline",
        "overview": "Approval rate dropped below its weekday baseline.",
        "dimension_signatures": signatures(),
        "related_incident_ids": [],
        "related_deployment_ids": [],
        "match_rationale": "The current signature is not present in recent incidents.",
        "estimated_impact": 1200.0,
        "approval_rate_drop": 12.5,
        "affected_transaction_count": 40,
        "started_at": datetime.now(UTC),
        "last_seen_at": datetime.now(UTC),
        **overrides,
    }


def test_dimension_signature_rejects_unknown_dimension():
    with pytest.raises(ValidationError):
        DimensionSignatures.model_validate({**signatures(), "currency": "ARS"})


def test_incident_decision_rejects_missing_required_mutable_field():
    payload = proposal()
    del payload["last_seen_at"]
    with pytest.raises(ValidationError):
        UpdatedIncidentProposal.model_validate({"incident_id": 7, **payload})


def test_incident_decision_rejects_invalid_lifecycle_value():
    with pytest.raises(ValidationError):
        UpdatedIncidentProposal.model_validate(
            {"incident_id": 7, **proposal(status="monitoring")}
        )


def test_strict_schema_requires_all_signature_properties():
    schema = response_format("anomaly_investigation", AnomalyInvestigation)["format"][
        "schema"
    ]
    signature_schema = schema["$defs"]["DimensionSignatures"]
    assert signature_schema["additionalProperties"] is False
    assert set(signature_schema["required"]) == set(signature_schema["properties"])


def test_parse_output_rejects_unknown_top_level_property():
    with pytest.raises(ValueError):
        parse_output(
            IncidentReviewDecision,
            '{"new_incidents": [], "updated_incidents": [], "extra": true}',
        )
