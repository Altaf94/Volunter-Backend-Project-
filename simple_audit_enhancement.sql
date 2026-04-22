-- Simple audit enhancement without requiring new columns
-- This just improves the action descriptions in the existing audit trail

BEGIN;

-- Update the existing audit function to provide better action descriptions
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

    -- Determine action type and description
    IF (TG_OP = 'INSERT') THEN
        v_action_type := 'INSERT';
        v_action_description := 'Form created';
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "ChangedAt", "ActionDescription"
        ) VALUES (
            NEW."FormId", v_action_type, NULL, 
            row_to_json(NEW), v_changed_by, NOW(), v_action_description
        );
        RETURN NEW;
        
    ELSIF (TG_OP = 'UPDATE') THEN
        -- Check for specific status transitions to provide better descriptions
        IF OLD."FormStatus" != NEW."FormStatus" THEN
            -- Status changed - provide specific descriptions
            IF OLD."FormStatus" = 2 AND NEW."FormStatus" = 3 THEN
                v_action_type := 'APPROVE';
                v_action_description := 'Form approved/submitted';
            ELSIF OLD."FormStatus" = 2 AND NEW."FormStatus" = 4 THEN
                v_action_type := 'REJECT';
                v_action_description := 'Form rejected';
            ELSIF OLD."FormStatus" = 4 AND NEW."FormStatus" = 2 THEN
                v_action_type := 'RESUBMIT';
                v_action_description := 'Form resubmitted for review';
            ELSIF OLD."FormStatus" = 1 AND NEW."FormStatus" = 2 THEN
                v_action_type := 'SUBMIT';
                v_action_description := 'Form submitted for review';
            ELSE
                v_action_type := 'UPDATE_STATUS';
                v_action_description := 'Form status changed from ' || OLD."FormStatus" || ' to ' || NEW."FormStatus";
            END IF;
        ELSE
            -- Regular field update
            v_action_type := 'UPDATE';
            v_action_description := 'Form updated';
        END IF;
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "ChangedAt", "ActionDescription"
        ) VALUES (
            NEW."FormId", v_action_type, row_to_json(OLD), 
            row_to_json(NEW), v_changed_by, NOW(), v_action_description
        );
        RETURN NEW;
        
    ELSIF (TG_OP = 'DELETE') THEN
        v_action_type := 'DELETE';
        v_action_description := 'Form deleted';
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "ChangedAt", "ActionDescription"
        ) VALUES (
            OLD."FormId", v_action_type, row_to_json(OLD), 
            NULL, v_changed_by, NOW(), v_action_description
        );
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMIT;
