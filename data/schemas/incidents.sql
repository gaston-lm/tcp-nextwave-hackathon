CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    incident_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('urgent', 'high', 'medium', 'low')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'monitoring', 'resolved')),
    country TEXT,
    provider_name TEXT,
    overview TEXT NOT NULL,
    estimated_impact DOUBLE PRECISION CHECK (estimated_impact >= 0),
    approval_rate_drop DOUBLE PRECISION CHECK (approval_rate_drop >= 0 AND approval_rate_drop <= 100),
    affected_transaction_count INTEGER NOT NULL DEFAULT 0 CHECK (affected_transaction_count >= 0),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    agent_action TEXT,
    agent_action_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE incidents ADD COLUMN IF NOT EXISTS is_read BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
