CREATE TABLE completions (
    tenant_uid UInt32,
    -- Storing as a UUID, but it cannot be used directly in sorting
    -- For optimization, when querying, always include the created_at_date
    -- https://clickhouse.com/docs/en/sql-reference/data-types/uuid
    id UUID,
    -- Auto generated from the id column, and used in sorting and partitioning
    created_at DateTime64(3) ALIAS UUIDv7ToDateTime(id),
    -- Agent identifier
    agent_id LowCardinality(String),
    -- Updated at, used as a versioning in the replacing merge tree.
    updated_at DateTime,
    -- Version ID
    version_id FixedString(32),
    version_model LowCardinality(String),
    -- Full version object, serialized as a json string
    version String,
    -- Input
    input_id FixedString(32),
    input_preview String,
    -- Messages part of the input, serialized as a json string
    input_messages String,
    -- Variables part of the input, serialized as a json string
    input_variables String,
    -- Output
    output_id FixedString(32),
    output_preview String,
    -- output messages, serialized as a json string
    output_messages String,
    -- output error, serialized as a json string. If empty the run was successful
    output_error String,
    -- full rendered list ofmessages sent for the final completion, not including the output messages.
    -- serialized as a json string
    messages String CODEC(ZSTD(3)),
    -- Duration stored in tenth of a second, 0 is used as a default value
    -- and should be ignored in aggregations
    -- Maxes out at 65535 = 6555.35 seconds = 100.92 minutes
    duration_ds UInt16,
    duration_seconds Float64 ALIAS duration_ds / 10,
    -- Cost stored in millionths of a USD, 0 is used as a default value
    -- and should be ignored in aggregations
    cost_millionth_usd UInt32,
    cost_usd Float64 ALIAS cost_millionth_usd / 1000000,
    -- Metadata. Non scalars are stored as stringified JSON
    metadata Map(String, String),
    -- The origin of the run
    source Enum('web' = 1, 'api' = 2, 'mcp' = 3),
    -- Traces
    traces Nested (
        kind String,
        model String,
        provider String,
        usage String,
        name String,
        tool_input_preview String,
        tool_output_preview String,
        duration_ds UInt16,
        cost_millionth_usd UInt32
    )
) -- ReplacingMergeTree https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/replacingmergetree
-- De-duplicates data base on the ORDER_BY clause
-- updated_at is used as a versioning key, so that the latest
-- updated run takes precedence
ENGINE = ReplacingMergeTree(updated_at) -- 
PARTITION BY toDate(UUIDv7ToDateTime(id)) -- Composite primary key, needs to be sparse
PRIMARY KEY (tenant_uid, toDate(UUIDv7ToDateTime(id)))
ORDER BY (
        tenant_uid,
        toDate(UUIDv7ToDateTime(id)),
        -- We should probably have order by UUIDv7ToDateTime(id) here to be consistent with the previous
        -- value. However from testing, it seems that clickhouse is capable of understanding 
        -- perfectly that UUIDv7ToDateTime(id) and toUInt128(id) are in the same order
        -- so changing this would not improve performance
        -- When https://clickhouse.com/docs/operations/settings/merge-tree-settings#allow_experimental_reverse_key
        -- is supported, we should change this to a reverse order so that completions are naturally ordered
        -- "most recent first" and so we can remove the "replace ORDER BY created_at DESC" hack
        toUInt128(id) -- Order by run uuid converted to datetime to avoid sorting error
    );
-- Using experimental reverse would be good here but it's not supported by clickhouse cloud yet
-- Add a bloom filters
-- For somewhat efficient retrieval
ALTER TABLE completions
ADD INDEX input_id_index input_id TYPE bloom_filter(0.01);
ALTER TABLE completions
ADD INDEX output_id_index output_id TYPE bloom_filter(0.01);
