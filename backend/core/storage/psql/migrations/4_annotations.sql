-- Annotations
CREATE TABLE annotations (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    slug VARCHAR(64) NOT NULL,
    target_experiment_uid BIGINT REFERENCES experiments(uid) ON DELETE CASCADE,
    target_completion_id VARCHAR(64),
    target_key_path TEXT,
    context_experiment_uid BIGINT REFERENCES experiments(uid) ON DELETE CASCADE,
    context_agent_uid BIGINT REFERENCES agents(uid) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    author_name TEXT NOT NULL,
    text TEXT,
    metric_name TEXT,
    metric_value_float DOUBLE PRECISION,
    metric_value_str TEXT,
    metric_value_bool BOOLEAN,
    metadata JSONB NOT NULL,
    CONSTRAINT annotations_tenant_uid_slug_unique UNIQUE (tenant_uid, slug)
);
ALTER TABLE annotations ENABLE ROW LEVEL SECURITY;
CREATE POLICY annotations_tenant_isolation_policy ON annotations USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
ALTER TABLE annotations
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
