drop table public.logs_processor_data;

create table if not exists public.logs_processor_data (
    request_id VARCHAR(36),
    payload JSONB,
    created_date TIMESTAMP,
    status VARCHAR(1)
);

select *
 from public.logs_processor_data
;

