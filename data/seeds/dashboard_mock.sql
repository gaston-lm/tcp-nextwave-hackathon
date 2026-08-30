INSERT INTO incidents (
    incident_id, title, severity, status, overview, dimension_signatures,
    estimated_impact, approval_rate_drop, affected_transaction_count, started_at, last_seen_at
) VALUES
    (3159, 'Mercado Pago declines transfers from AR', 'urgent', 'open',
     'Authorization declines are above the expected baseline for Argentine bank transfers.',
     '{"merchant": null, "provider": "Mercado Pago", "payment_method": "transfer", "country": "Argentina", "issuing_bank": null}',
     5120000, 18.7, 1284, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (3160, 'Naranja X transfer latency elevated', 'high', 'open',
     'P95 transfer latency is above the operational threshold for the provider.',
     '{"merchant": null, "provider": "Naranja X", "payment_method": "transfer", "country": "Argentina", "issuing_bank": null}',
     860000, 9.4, 642, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (3158, 'PIX confirmation delays', 'high', 'closed',
     'Delayed confirmations affected a subset of PIX transfers.',
     '{"merchant": null, "provider": "PIX", "payment_method": "transfer", "country": "Brazil", "issuing_bank": null}',
     290000, 7.1, 203, CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days')
ON CONFLICT (incident_id) DO UPDATE SET
    title = EXCLUDED.title,
    severity = EXCLUDED.severity,
    status = EXCLUDED.status,
    overview = EXCLUDED.overview,
    dimension_signatures = EXCLUDED.dimension_signatures,
    estimated_impact = EXCLUDED.estimated_impact,
    approval_rate_drop = EXCLUDED.approval_rate_drop,
    affected_transaction_count = EXCLUDED.affected_transaction_count,
    started_at = EXCLUDED.started_at,
    last_seen_at = EXCLUDED.last_seen_at;

SELECT setval(pg_get_serial_sequence('incidents', 'incident_id'), (SELECT MAX(incident_id) FROM incidents));
