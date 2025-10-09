-- Nested objects are stored as array of fields
ALTER TABLE completions
ADD COLUMN IF NOT EXISTS traces.prompt_tokens Array(UInt32)
AFTER traces.cost_millionth_usd,
    ADD COLUMN IF NOT EXISTS traces.completion_tokens Array(UInt32)
AFTER traces.prompt_tokens,
    ADD COLUMN IF NOT EXISTS traces.reasoning_tokens Array(UInt32)
AFTER traces.completion_tokens,
    ADD COLUMN IF NOT EXISTS traces.cached_tokens Array(UInt32)
AFTER traces.reasoning_tokens;
-- Add comment for each field
ALTER TABLE completions COMMENT COLUMN traces.usage 'Detailed information about the usage, stored as a stringified JSON';
