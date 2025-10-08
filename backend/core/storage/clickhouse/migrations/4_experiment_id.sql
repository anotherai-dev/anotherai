ALTER TABLE completions
ADD COLUMN experiment_id String ALIAS metadata ['anotherai/experiment_id'];
-- Add description to field experiment_id field
ALTER TABLE completions
MODIFY COLUMN experiment_id String COMMENT 'The ID of the experiment that this completion belongs to. Mapping to metadata field anotherai/experiment_id.';
ALTER TABLE experiments DROP COLUMN completion_ids;
