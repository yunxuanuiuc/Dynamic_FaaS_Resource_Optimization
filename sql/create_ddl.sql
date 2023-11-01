create table if not exists logs_processor_data (
    request_id NUMERIC,
    payload JSONB,
    created_date TIMESTAMP,
    status VARCHAR(1)
);
