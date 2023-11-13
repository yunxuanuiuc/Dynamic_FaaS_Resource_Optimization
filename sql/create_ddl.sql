drop table if exists public.logs_processor_data;

create table if not exists public.logs_processor_data (
    request_id VARCHAR(36),
    function_name VARCHAR(64),
    payload JSONB,
    created_date TIMESTAMP,
    status VARCHAR(1)
);

