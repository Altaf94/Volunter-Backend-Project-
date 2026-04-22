-- Fix FormAudit Action column to accommodate longer action types
BEGIN;

-- Increase Action column size to handle all action types
ALTER TABLE "FormAudit" 
    ALTER COLUMN "Action" TYPE VARCHAR(30);

COMMIT;

-- This fixes the error: value too long for type character varying(10)
-- Action types that need more than 10 characters:
-- - UPDATE_STATUS (13 chars)
-- - SUBMIT_FOR_REVIEW (18 chars)

