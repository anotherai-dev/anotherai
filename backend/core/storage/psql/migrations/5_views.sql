-- View Folders
CREATE TABLE view_folders (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    slug VARCHAR(64) NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    CONSTRAINT view_folders_tenant_uid_slug_unique UNIQUE (tenant_uid, slug)
);
ALTER TABLE view_folders ENABLE ROW LEVEL SECURITY;
CREATE POLICY view_folders_tenant_isolation_policy ON view_folders USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
ALTER TABLE view_folders
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
-- Views
CREATE TABLE views (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    slug VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    folder_uid BIGINT REFERENCES view_folders(uid) ON DELETE CASCADE,
    --
    position INT NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    query TEXT NOT NULL,
    graph_type VARCHAR(64) NOT NULL DEFAULT '',
    graph JSONB,
    CONSTRAINT views_folder_uid_slug_unique UNIQUE (tenant_uid, slug)
);
ALTER TABLE views ENABLE ROW LEVEL SECURITY;
CREATE POLICY views_tenant_isolation_policy ON views USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
ALTER TABLE views
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
-- Create an index for efficient retrieval of views ordered by position and updated_at
CREATE INDEX views_by_position ON views (
    tenant_uid ASC,
    position ASC,
    updated_at DESC
);
