-- Experiment inputs
ALTER TABLE experiment_inputs
ADD COLUMN position INTEGER,
    ADD COLUMN alias VARCHAR(255),
    ADD CONSTRAINT experiment_inputs_alias_unique UNIQUE (experiment_uid, alias);
CREATE UNIQUE INDEX experiment_inputs_position_unique ON experiment_inputs (experiment_uid, position)
WHERE position IS NOT NULL;
-- Experiment versions
ALTER TABLE experiment_versions
ADD COLUMN position INTEGER,
    ADD COLUMN alias VARCHAR(255),
    ADD CONSTRAINT experiment_versions_alias_unique UNIQUE (experiment_uid, alias);
CREATE UNIQUE INDEX experiment_versions_position_unique ON experiment_versions (experiment_uid, position)
WHERE position IS NOT NULL;
