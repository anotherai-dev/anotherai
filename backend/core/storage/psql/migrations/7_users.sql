CREATE TABLE users (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id VARCHAR(255) NOT NULL UNIQUE,
    last_used_organization_uid BIGINT REFERENCES tenants(uid)
);
