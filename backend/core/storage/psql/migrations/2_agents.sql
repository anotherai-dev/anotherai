-- Agents
CREATE TABLE agents (
    uid BIGINT PRIMARY KEY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    slug VARCHAR(64) NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    CONSTRAINT agents_tenant_uid_slug_unique UNIQUE (tenant_uid, slug)
);
-- set a default value for tenant_uid for inserts
ALTER TABLE agents
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
CREATE POLICY agents_tenant_isolation_policy ON agents FOR ALL USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
