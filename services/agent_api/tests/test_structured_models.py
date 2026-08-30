from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from services.agent_api.app.agents.action_taker import ActionTaker
from services.agent_api.app.agents.incident_reviewer import IncidentReviewer
from services.agent_api.app.incidents import normalized_dimension_signatures
from services.agent_api.app.metrics import MetricsService
from services.agent_api.app.models.anomaly_detection import (
    ActionableIncident,
    ActionProposal,
    AnomalyInvestigation,
    DimensionSignatures,
    IncidentReviewDecision,
    RecentIncident,
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


def test_action_proposal_rejects_unknown_action_type():
    with pytest.raises(ValidationError):
        ActionProposal.model_validate(
            {
                "incident_id": 7,
                "action_type": "send_provider_email",
                "action_details": "Draft message",
            }
        )


def test_action_proposal_requires_operator_guidance():
    with pytest.raises(ValidationError):
        ActionProposal.model_validate(
            {
                "incident_id": 7,
                "action_type": "deploy_rollback",
                "action_details": "",
            }
        )


def actionable_incident(**overrides):
    return ActionableIncident.model_validate(
        {
            "incident_id": 7,
            "title": "Authorization declines",
            "overview": "Approval rates fell.",
            "dimension_signatures": signatures(merchant="Merchant A"),
            "related_deployment_ids": [],
            **overrides,
        }
    )


def action_proposal(action_type, details):
    return ActionProposal(
        incident_id=7, action_type=action_type, action_details=details
    )


def test_action_taker_requires_deployment_rollback_before_other_actions():
    incident = actionable_incident(related_deployment_ids=["deploy-123"])
    with pytest.raises(ValueError, match="require rollback"):
        ActionTaker.validate_proposal(
            incident,
            action_proposal("post_slack_alert_to_channel", "Draft Slack alert"),
            ["Provider B"],
        )
    ActionTaker.validate_proposal(
        incident,
        action_proposal("deploy_rollback", "Investigate rollback of deploy-123."),
        ["Provider B"],
    )


def test_action_taker_requires_approved_provider_switch_when_available():
    incident = actionable_incident()
    with pytest.raises(ValueError, match="require a switch"):
        ActionTaker.validate_proposal(
            incident,
            action_proposal("post_slack_alert_to_channel", "Draft Slack alert"),
            ["Provider B"],
        )
    ActionTaker.validate_proposal(
        incident,
        action_proposal(
            "recommend_switch_provider_to_merchant",
            "Recommend Provider B; draft provider escalation.",
        ),
        ["Provider B"],
    )


def test_action_taker_falls_back_to_slack_without_provider_alternatives():
    incident = actionable_incident()
    ActionTaker.validate_proposal(
        incident,
        action_proposal("post_slack_alert_to_channel", "Draft Slack alert"),
        [],
    )


def test_sparse_database_signature_is_normalized_for_strict_agent_models():
    assert normalized_dimension_signatures({"provider": "MercadoPago"}) == {
        "merchant": None,
        "provider": "MercadoPago",
        "payment_method": None,
        "country": None,
        "issuing_bank": None,
    }


def test_metrics_exposes_a_timezone_aware_observation_window():
    metrics = MetricsService(
        pool=None,
        as_of=datetime(2026, 8, 30, 3, 7, 40, tzinfo=UTC),
    )

    assert metrics.observation_window_start == datetime(2026, 8, 30, 3, 0, tzinfo=UTC)
    assert metrics.observation_window_end == datetime(2026, 8, 30, 3, 5, tzinfo=UTC)


def test_reviewer_derives_proposal_timestamps_from_observation_window():
    original_started_at = datetime(2026, 8, 30, 2, 30, tzinfo=UTC)
    window_start = datetime(2026, 8, 30, 3, 0, tzinfo=UTC)
    window_end = datetime(2026, 8, 30, 3, 5, tzinfo=UTC)
    decision = IncidentReviewDecision.model_validate(
        {
            "new_incidents": [proposal()],
            "updated_incidents": [{"incident_id": 7, **proposal()}],
        }
    )
    recent_incident = RecentIncident.model_validate(
        {
            "incident_id": 7,
            "severity": "high",
            "status": "open",
            "title": "Acquirer authorization decline",
            "overview": "Approval rate dropped below its weekday baseline.",
            "dimension_signatures": signatures(),
            "estimated_impact": 1200.0,
            "approval_rate_drop": 12.5,
            "affected_transaction_count": 40,
            "started_at": original_started_at,
            "last_seen_at": original_started_at,
        }
    )

    result = IncidentReviewer._timestamp_decision(
        decision, [recent_incident], window_start, window_end
    )

    assert result.new_incidents[0].started_at == window_start
    assert result.new_incidents[0].last_seen_at == window_end
    assert result.updated_incidents[0].started_at == original_started_at
    assert result.updated_incidents[0].last_seen_at == window_end
