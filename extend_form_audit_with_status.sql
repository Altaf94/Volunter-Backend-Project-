-- Extend Form audit to include status transitions (OldStatus/NewStatus)

BEGIN;

-- Add columns if they do not exist
ALTER TABLE "FormAudit"
    ADD COLUMN IF NOT EXISTS "OldStatus" INTEGER,
    ADD COLUMN IF NOT EXISTS "NewStatus" INTEGER;

-- Update audit function to populate status transition fields
CREATE OR REPLACE FUNCTION fn_form_audit() RETURNS TRIGGER AS $$
DECLARE
    v_changed_by TEXT;
BEGIN
    -- Optionally pull from a session variable if the app sets it
    BEGIN
        v_changed_by := current_setting('application.user_id', true);
    EXCEPTION WHEN others THEN
        v_changed_by := NULL;
    END;

    IF (TG_OP = 'INSERT') THEN
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", "OldStatus", "NewStatus"
        ) VALUES (
            NEW."FormId", 'INSERT', NULL, to_jsonb(NEW), v_changed_by, NULL, NEW."FormStatus"
        );
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", "OldStatus", "NewStatus"
        ) VALUES (
            NEW."FormId", 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), v_changed_by, OLD."FormStatus", NEW."FormStatus"
        );
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", "OldStatus", "NewStatus"
        ) VALUES (
            OLD."FormId", 'DELETE', to_jsonb(OLD), NULL, v_changed_by, OLD."FormStatus", NULL
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMIT;


