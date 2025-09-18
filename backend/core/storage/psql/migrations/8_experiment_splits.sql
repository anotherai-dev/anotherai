-- Experiment inputs
CREATE TABLE experiment_inputs (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    experiment_uid BIGINT NOT NULL REFERENCES experiments(uid) ON DELETE CASCADE,
    input_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    input_messages JSONB,
    input_variables JSONB,
    -- No duplicate inputs within an experiment
    CONSTRAINT experiment_inputs_experiment_input_unique UNIQUE (experiment_uid, input_id)
);
ALTER TABLE experiment_inputs ENABLE ROW LEVEL SECURITY;
CREATE POLICY experiment_inputs_tenant_isolation_policy ON experiment_inputs USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
ALTER TABLE experiment_inputs
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
-- ------------------------------------------------------------
-- Experiment versions
CREATE TABLE experiment_versions (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    experiment_uid BIGINT NOT NULL REFERENCES experiments(uid) ON DELETE CASCADE,
    version_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    model VARCHAR(64) NOT NULL,
    -- Storing everything in a JSONB instead of separate columns
    -- Most of the fields will likely be null anyway
    payload JSONB NOT NULL,
    CONSTRAINT experiment_versions_experiment_version_unique UNIQUE (experiment_uid, version_id)
);
ALTER TABLE experiment_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY experiment_versions_tenant_isolation_policy ON experiment_versions USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
ALTER TABLE experiment_versions
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
-- ------------------------------------------------------------
-- Add experiment completion ids
CREATE TABLE experiment_outputs (
    uid BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_uid BIGINT NOT NULL REFERENCES tenants(uid) ON DELETE CASCADE,
    experiment_uid BIGINT NOT NULL REFERENCES experiments(uid) ON DELETE CASCADE,
    version_uid BIGINT NOT NULL REFERENCES experiment_versions(uid) ON DELETE CASCADE,
    input_uid BIGINT NOT NULL REFERENCES experiment_inputs(uid) ON DELETE CASCADE,
    completion_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    deleted_at TIMESTAMP,
    completed_at TIMESTAMP,
    output_messages JSONB,
    output_error JSONB,
    output_preview VARCHAR(255),
    CONSTRAINT experiment_outputs_experiment_version_input_unique UNIQUE (experiment_uid, version_uid, input_uid),
    CONSTRAINT experiment_outputs_experiment_completion_unique UNIQUE (experiment_uid, completion_id)
);
ALTER TABLE experiment_outputs ENABLE ROW LEVEL SECURITY;
CREATE POLICY experiment_outputs_tenant_isolation_policy ON experiment_outputs USING (
    tenant_uid = current_setting('app.tenant_uid')::BIGINT
);
ALTER TABLE experiment_outputs
ALTER COLUMN tenant_uid
SET DEFAULT current_setting('app.tenant_uid')::BIGINT;
-- ------------------------------------------------------------
-- Once migrated we should remove the run_ids column from the experiments
ALTER TABLE experiments
ADD COLUMN use_cache VARCHAR(64);
