CREATE TABLE methods_by_provider (
    provider_id INT,
    provider_name TEXT,
    method_id INT,
    method_name TEXT,

    PRIMARY KEY (provider_id, method_id)
);