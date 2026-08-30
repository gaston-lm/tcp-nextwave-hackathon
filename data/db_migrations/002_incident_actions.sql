CREATE TABLE IF NOT EXISTS incidents_actions (
    action_id SERIAL PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (
        action_type IN (
            'deploy_rollback',
            'recommend_switch_provider_to_merchant',
            'post_slack_alert_to_channel'
        )
    ),
    action_details TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_actions_incident_id
    ON incidents_actions (incident_id);
