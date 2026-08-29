-- Enables ingestion/data/example.csv in the local Docker database.
INSERT INTO providers_by_merchant (merchant_id, merchant_name, provider_id, provider_name)
VALUES (1001, 'Example Merchant', 1, 'ExamplePay')
ON CONFLICT (merchant_id, provider_id) DO NOTHING;

INSERT INTO methods_by_provider (provider_id, provider_name, method_id, method_name)
VALUES (1, 'ExamplePay', 1, 'credit_card')
ON CONFLICT (provider_id, method_id) DO NOTHING;
