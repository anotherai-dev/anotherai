CREATE TABLE deployments (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    agent_uid BIGINT NOT NULL REFERENCES agents(uid) ON DELETE CASCADE,
    slug VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    version_id VARCHAR(64) NOT NULL,
    version JSONB NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    metadata JSONB,
    CONSTRAINT deployments_tenant_uid_slug_unique UNIQUE (tenant_uid, slug)
);
ALTER TABLE deployments ENABLE ROW LEVEL SECURITY;
CREATE POLICY deployments_tenant_isolation_policy ON deployments USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
ALTER TABLE deployments
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
-- Efficient retrieval of deployments by agent_id
CREATE INDEX deployments_by_agent_id ON deployments (
    tenant_uid ASC,
    agent_uid ASC,
    updated_at DESC
);
