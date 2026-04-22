-- Enhance Form audit to explicitly track approval and rejection actions
-- This creates more descriptive audit trail entries for approval/rejection

BEGIN;

-- Update audit function to detect and label approval/rejection actions
CREATE OR REPLACE FUNCTION fn_form_audit() RETURNS TRIGGER AS $$
DECLARE
    v_changed_by TEXT;
    v_action_type TEXT;
    v_action_description TEXT;
BEGIN
    -- Get the acting user from session variable
    BEGIN
        v_changed_by := current_setting('application.user_id', true);
    EXCEPTION WHEN others THEN
        v_changed_by := NULL;
    END;

    -- Determine action type and description based on status transitions
    IF (TG_OP = 'INSERT') THEN
        v_action_type := 'INSERT';
        v_action_description := 'Form created';
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "OldStatus", "NewStatus", "ActionType", "ActionDescription"
        ) VALUES (
            NEW."FormId", 'INSERT', NULL, to_jsonb(NEW), v_changed_by, 
            NULL, NEW."FormStatus", v_action_type, v_action_description
        );
        RETURN NEW;
        
    ELSIF (TG_OP = 'UPDATE') THEN
        -- Detect approval/rejection actions based on status transitions
        IF OLD."FormStatus" = 2 AND NEW."FormStatus" = 3 THEN
            -- Approved (Under Review -> Submitted/Approved)
            v_action_type := 'APPROVE';
            v_action_description := 'Form approved by checker';
        ELSIF OLD."FormStatus" = 2 AND NEW."FormStatus" = 4 THEN
            -- Rejected (Under Review -> Rejected)
            v_action_type := 'REJECT';
            v_action_description := 'Form rejected by checker';
        ELSIF OLD."FormStatus" = 4 AND NEW."FormStatus" = 1 THEN
            -- Resubmitted (Rejected -> Pending)
            v_action_type := 'RESUBMIT';
            v_action_description := 'Form resubmitted after rejection';
        ELSIF OLD."FormStatus" = 1 AND NEW."FormStatus" = 2 THEN
            -- Submitted for Review (Pending -> Under Review)
            v_action_type := 'SUBMIT_FOR_REVIEW';
            v_action_description := 'Form submitted for review';
        ELSE
            -- Generic update
            v_action_type := 'UPDATE';
            v_action_description := 'Form updated';
        END IF;
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "OldStatus", "NewStatus", "ActionType", "ActionDescription"
        ) VALUES (
            NEW."FormId", 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), v_changed_by, 
            OLD."FormStatus", NEW."FormStatus", v_action_type, v_action_description
        );
        RETURN NEW;
        
    ELSIF (TG_OP = 'DELETE') THEN
        v_action_type := 'DELETE';
        v_action_description := 'Form deleted';
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "OldStatus", "NewStatus", "ActionType", "ActionDescription"
        ) VALUES (
            OLD."FormId", 'DELETE', to_jsonb(OLD), NULL, v_changed_by, 
            OLD."FormStatus", NULL, v_action_type, v_action_description
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Add new columns to FormAudit table if they don't exist
ALTER TABLE "FormAudit" 
    ADD COLUMN IF NOT EXISTS "ActionType" VARCHAR(20),
    ADD COLUMN IF NOT EXISTS "ActionDescription" VARCHAR(100);

-- Add comments for documentation
COMMENT ON COLUMN "FormAudit"."ActionType" IS 'Specific action type: APPROVE, REJECT, RESUBMIT, SUBMIT_FOR_REVIEW, UPDATE, INSERT, DELETE';
COMMENT ON COLUMN "FormAudit"."ActionDescription" IS 'Human-readable description of the action performed';

-- Create index for better query performance on ActionType
CREATE INDEX IF NOT EXISTS idx_formaudit_actiontype ON "FormAudit"("ActionType");

COMMIT;
