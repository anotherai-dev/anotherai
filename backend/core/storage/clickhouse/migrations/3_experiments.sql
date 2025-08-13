-- Table will be very small so for now we are not optimizing it at all
CREATE TABLE experiments (
    tenant_uid UInt32,
    created_at DateTime,
    updated_at DateTime,
    id String,
    completion_ids Array(UUID),
    agent_id LowCardinality(String),
    metadata Map(String, String),
    title String,
    description String,
    result Nullable(String),
) ENGINE = ReplacingMergeTree(updated_at) -- 
PRIMARY KEY (tenant_uid, agent_id, toDate(created_at))
ORDER BY (
        tenant_uid,
        agent_id,
        toDate(created_at),
        id
    ) SETTINGS allow_experimental_reverse_key = 1;
