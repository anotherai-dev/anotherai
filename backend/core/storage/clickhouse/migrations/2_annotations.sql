-- Table will be very small so for now we are not optimizing it at all
CREATE TABLE annotations (
    tenant_uid UInt32,
    created_at DateTime,
    id String,
    updated_at DateTime,
    agent_id LowCardinality(String),
    completion_id UUID,
    metric_name Nullable(String),
    metric_value_float Nullable(Float64),
    metric_value_str Nullable(String),
    metric_value_bool Nullable(Boolean),
    metadata Map(String, String),
    author_name String,
    text Nullable(String),
) ENGINE = ReplacingMergeTree(updated_at) -- 
PRIMARY KEY (tenant_uid, agent_id, toDate(created_at))
ORDER BY (
        tenant_uid,
        agent_id,
        toDate(created_at) DESC,
        id
    ) SETTINGS allow_experimental_reverse_key = 1;
