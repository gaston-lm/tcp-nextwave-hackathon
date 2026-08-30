CREATE TABLE transactions (
    country TEXT,
    provider_name TEXT,
    provider_id INT,
    method_name TEXT,
    method_id INT,
    merchant_name TEXT,
    merchant_id INT,
    issuing_bank TEXT,
    receiving_bank TEXT,
    transaction_id INT PRIMARY KEY,
    issued_timestamp TIMESTAMP,
    is_declined BOOLEAN,
    decline_code BIGINT, -- ISO-8583
    currency TEXT,
    value_transaction_currency DOUBLE PRECISION,
    value DOUBLE PRECISION,

    FOREIGN KEY (provider_id, method_id)
        REFERENCES methods_by_provider (provider_id, method_id),

    FOREIGN KEY (merchant_id, provider_id)
        REFERENCES providers_by_merchant (merchant_id, provider_id)
);

-- Supports dashboard queries anchored on the newest transaction and grouped by hour.
CREATE INDEX IF NOT EXISTS transactions_issued_timestamp_idx
    ON transactions (issued_timestamp);
