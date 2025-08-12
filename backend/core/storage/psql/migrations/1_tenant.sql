-- Tenants
CREATE TABLE tenants (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    slug VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    providers JSONB NOT NULL DEFAULT '[]',
    -- Org data
    owner_id VARCHAR(255),
    org_id VARCHAR(255),
    -- Payment
    current_credits_usd FLOAT NOT NULL DEFAULT 0.0,
    stripe_customer_id VARCHAR(255),
    locked_for_payment BOOLEAN NOT NULL DEFAULT FALSE,
    automatic_payment_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    automatic_payment_threshold FLOAT,
    automatic_payment_balance_to_maintain FLOAT,
    payment_failure_date TIMESTAMP,
    payment_failure_code VARCHAR(255),
    payment_failure_reason TEXT,
    low_credits_email_sent_by_threshold JSONB,
    provider_configs JSONB NOT NULL DEFAULT '[]'
);
CREATE UNIQUE INDEX tenants_org_id_unique ON tenants (org_id)
WHERE org_id IS NOT NULL;
CREATE UNIQUE INDEX tenants_owner_id_unique_if_org_id_null ON tenants (owner_id)
WHERE org_id IS NULL;
-- Can't create a policy on tenants since we need to fetch a tenant by slug
-- API Keys
CREATE TABLE api_keys (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    slug VARCHAR(64) NOT NULL,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    partial_key VARCHAR(32) NOT NULL,
    hashed_key VARCHAR(64) NOT NULL UNIQUE,
    last_used_at TIMESTAMP,
    -- Constraints
    CONSTRAINT api_keys_tenant_uid_slug_unique UNIQUE (tenant_uid, slug)
);
