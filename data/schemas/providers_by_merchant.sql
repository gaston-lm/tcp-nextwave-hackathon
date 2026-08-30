CREATE TABLE providers_by_merchant (
    merchant_id INT,
    merchant_name TEXT,
    provider_id INT,
    provider_name TEXT,

    PRIMARY KEY (merchant_id, provider_id)
);