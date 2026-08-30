CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS incidents (
    incident_id SERIAL PRIMARY KEY,
    severity TEXT NOT NULL CHECK (severity IN ('urgent', 'high', 'medium', 'low')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed', 'needs_action')),
    title TEXT NOT NULL,
    overview TEXT NOT NULL,
    dimension_signatures JSONB NOT NULL,
    related_incidents INTEGER[] NOT NULL DEFAULT '{}'::INTEGER[],
    related_deployments TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    estimated_impact DOUBLE PRECISION CHECK (estimated_impact >= 0),
    approval_rate_drop DOUBLE PRECISION CHECK (approval_rate_drop >= 0 AND approval_rate_drop <= 100),
    affected_transaction_count INTEGER NOT NULL DEFAULT 0 CHECK (affected_transaction_count >= 0),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        jsonb_typeof(dimension_signatures) = 'object'
        AND dimension_signatures - ARRAY['merchant', 'provider', 'payment_method', 'country', 'issuing_bank'] = '{}'::JSONB
    )
);

CREATE TABLE IF NOT EXISTS incident_memory (
    incident_id INTEGER PRIMARY KEY REFERENCES incidents(incident_id) ON DELETE CASCADE,
    searchable_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deployment_logs (
    deploy_id TEXT PRIMARY KEY,
    description_of_deploy TEXT NOT NULL,
    dimensions_affected JSONB NOT NULL DEFAULT '{}'::JSONB,
    embedding vector(1536) NOT NULL,
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (jsonb_typeof(dimensions_affected) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_open_last_seen ON incidents(status, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_incident_memory_embedding ON incident_memory USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_deployment_logs_embedding ON deployment_logs USING hnsw (embedding vector_cosine_ops);
