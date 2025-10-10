CREATE TABLE experiments (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    agent_uid BIGINT NOT NULL REFERENCES agents(uid) ON DELETE CASCADE,
    slug VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author_name TEXT NOT NULL,
    deleted_at TIMESTAMP,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    result TEXT,
    run_ids VARCHAR(64) [],
    metadata JSONB NOT NULL,
    CONSTRAINT experiments_tenant_uid_slug_unique UNIQUE (tenant_uid, slug)
);
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
CREATE POLICY experiments_tenant_isolation_policy ON experiments USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
ALTER TABLE experiments
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
