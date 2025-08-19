-- Add reasoning token count column to completions table
ALTER TABLE completions ADD COLUMN reasoning_token_count Nullable(UInt32) DEFAULT NULL;