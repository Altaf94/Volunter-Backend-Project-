BEGIN;

-- Add LastActionBy to Form to track who last changed status
ALTER TABLE "Form"
    ADD COLUMN IF NOT EXISTS "LastActionBy" VARCHAR(50);

-- Ensure no FK constraint exists on LastActionBy
DO $$
DECLARE
    _constraint_name text;
BEGIN
    SELECT constraint_name INTO _constraint_name
    FROM information_schema.table_constraints
    WHERE table_name = 'Form' AND constraint_type = 'FOREIGN KEY';
    IF _constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE "Form" DROP CONSTRAINT IF EXISTS %I', _constraint_name);
    END IF;
END $$;

COMMIT;


