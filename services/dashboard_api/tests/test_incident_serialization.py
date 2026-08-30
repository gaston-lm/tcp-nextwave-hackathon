from services.dashboard_api.main import serialize_incident


def incident_row(actions=None):
    return (
        7,
        "Authorization declines",
        "high",
        "open",
        "Approval rates fell.",
        '{"merchant": "Merchant A", "provider": "Provider A"}',
        1200.0,
        12.5,
        40,
        "2026-08-30T12:00:00Z",
        "2026-08-30T12:05:00Z",
        False,
        [],
        [],
        actions or [],
        "2026-08-30T12:00:00Z",
    )


def test_serializes_persisted_action_for_dashboard():
    result = serialize_incident(
        incident_row(
            [
                {
                    "actionType": "post_slack_alert_to_channel",
                    "actionDetails": "Draft Slack alert for Merchant A.",
                    "createdAt": "2026-08-30T12:06:00Z",
                }
            ]
        )
    )

    assert result["agentAction"] == "Draft Slack alert for Merchant A."
    assert result["agentActionType"] == "post_slack_alert_to_channel"
    assert result["agentActionAt"] == "2026-08-30T12:06:00Z"
    assert result["actions"] == [
        {
            "actionType": "post_slack_alert_to_channel",
            "actionDetails": "Draft Slack alert for Merchant A.",
            "createdAt": "2026-08-30T12:06:00Z",
        }
    ]


def test_serializes_absent_action_as_null():
    result = serialize_incident(incident_row())

    assert result["agentAction"] is None
    assert result["actions"] == []
    assert result["agentActionAt"] is None
