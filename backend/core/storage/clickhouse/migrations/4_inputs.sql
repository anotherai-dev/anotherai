CREATE TABLE inputs (
    tenant_uid UInt32,
    input_id FixedString(32),
    input_preview String,
    -- Messages part of the input, serialized as a json string
    input_messages String,
    -- Variables part of the input, serialized as a json string
    input_variables String,
    created_at DateTime64(3),
    agent_id LowCardinality(String),
    metadata Map(String, String),
) -- Use a replacing merge tree to only store one input by ORDER BY
-- Latest input is the one with the latest created_at
ENGINE = ReplacingMergeTree(created_at) PRIMARY KEY (tenant_uid, agent_id)
ORDER BY (tenant_uid, agent_id, input_id);
