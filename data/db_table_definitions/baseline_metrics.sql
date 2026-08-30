-- Historical weekday acceptance baselines at every diagnostic grain.
-- dimensions_mask bit order: merchant=16, provider=8, payment_method=4,
-- country=2, issuing_bank=1. A set bit means the dimension belongs to the grain.
CREATE TABLE IF NOT EXISTS baseline_metrics (
    baseline_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    weekday SMALLINT NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    dimensions_mask SMALLINT NOT NULL CHECK (dimensions_mask BETWEEN 0 AND 31),
    merchant_name TEXT,
    provider_name TEXT,
    method_name TEXT,
    country TEXT,
    issuing_bank TEXT,
    attempts BIGINT NOT NULL CHECK (attempts >= 0),
    approvals BIGINT NOT NULL CHECK (approvals >= 0),
    declines BIGINT NOT NULL CHECK (declines >= 0),
    approval_rate DOUBLE PRECISION GENERATED ALWAYS AS (
        approvals::DOUBLE PRECISION / NULLIF(attempts, 0)
    ) STORED,
    decline_rate DOUBLE PRECISION GENERATED ALWAYS AS (
        declines::DOUBLE PRECISION / NULLIF(attempts, 0)
    ) STORED,
    history_start TIMESTAMP NOT NULL,
    history_end TIMESTAMP NOT NULL,
    refreshed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (approvals + declines = attempts),
    CHECK (history_start < history_end)
);

-- Allows existing local volumes to migrate from the previous weekday + time-slot
-- grain. Baselines are derived data and are rebuilt by refresh_baseline_metrics.
ALTER TABLE baseline_metrics DROP COLUMN IF EXISTS bucket_start;

CREATE INDEX IF NOT EXISTS baseline_metrics_lookup_idx ON baseline_metrics (
    weekday, dimensions_mask,
    merchant_name, provider_name, method_name, country, issuing_bank
);

-- Rebuild the baseline after history has been loaded. CUBE creates the global
-- grain plus every non-empty combination of the five diagnostic dimensions.
CREATE OR REPLACE FUNCTION refresh_baseline_metrics(
    p_history_start TIMESTAMP,
    p_history_end TIMESTAMP
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE baseline_metrics;

    INSERT INTO baseline_metrics (
        weekday, dimensions_mask,
        merchant_name, provider_name, method_name, country, issuing_bank,
        attempts, approvals, declines, history_start, history_end
    )
    SELECT
        EXTRACT(ISODOW FROM issued_timestamp)::SMALLINT,
        31 - GROUPING(merchant_name, provider_name, method_name, country, issuing_bank),
        merchant_name, provider_name, method_name, country, issuing_bank,
        COUNT(*),
        COUNT(*) FILTER (WHERE is_declined IS NOT TRUE),
        COUNT(*) FILTER (WHERE is_declined IS TRUE),
        p_history_start,
        p_history_end
    FROM transactions
    WHERE issued_timestamp >= p_history_start
      AND issued_timestamp < p_history_end
    GROUP BY
        EXTRACT(ISODOW FROM issued_timestamp),
        CUBE (merchant_name, provider_name, method_name, country, issuing_bank);
END;
$$;
