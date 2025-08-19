-- Add index on reasoning_token_count for efficient filtering and sorting
-- This enables fast queries like:
-- - Filtering completions with/without reasoning tokens
-- - Sorting by reasoning token count
-- - Aggregating reasoning token usage
ALTER TABLE completions ADD INDEX reasoning_token_count_index reasoning_token_count TYPE minmax;