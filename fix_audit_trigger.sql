-- Fix audit trigger to work with existing FormAudit table structure
-- This removes references to non-existent columns and provides better action descriptions

BEGIN;

-- Update the existing audit function to work with current table structure
CREATE OR REPLACE FUNCTION fn_form_audit() RETURNS TRIGGER AS $$
DECLARE
    v_changed_by TEXT;
    v_action_type TEXT;
BEGIN
    -- Get the acting user from session variable
    BEGIN
        v_changed_by := current_setting('application.user_id', true);
    EXCEPTION WHEN others THEN
        v_changed_by := NULL;
    END;

    -- Determine action type based on operation and status changes
    IF (TG_OP = 'INSERT') THEN
        v_action_type := 'INSERT';
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "ChangedAt"
        ) VALUES (
            NEW."FormId", v_action_type, NULL, 
            row_to_json(NEW), v_changed_by, NOW()
        );
        RETURN NEW;
        
    ELSIF (TG_OP = 'UPDATE') THEN
        -- Check for specific status transitions to provide better descriptions
        IF OLD."FormStatus" != NEW."FormStatus" THEN
            -- Status changed - provide specific action types
            IF OLD."FormStatus" = 2 AND NEW."FormStatus" = 3 THEN
                v_action_type := 'APPROVE';
            ELSIF OLD."FormStatus" = 2 AND NEW."FormStatus" = 4 THEN
                v_action_type := 'REJECT';
            ELSIF OLD."FormStatus" = 4 AND NEW."FormStatus" = 2 THEN
                v_action_type := 'RESUBMIT';
            ELSIF OLD."FormStatus" = 1 AND NEW."FormStatus" = 2 THEN
                v_action_type := 'SUBMIT';
            ELSE
                v_action_type := 'UPDATE_STATUS';
            END IF;
        ELSE
            -- Regular field update
            v_action_type := 'UPDATE';
        END IF;
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "ChangedAt"
        ) VALUES (
            NEW."FormId", v_action_type, row_to_json(OLD), 
            row_to_json(NEW), v_changed_by, NOW()
        );
        RETURN NEW;
        
    ELSIF (TG_OP = 'DELETE') THEN
        v_action_type := 'DELETE';
        
        INSERT INTO "FormAudit" (
            "FormId", "Action", "OldData", "NewData", "ChangedBy", 
            "ChangedAt"
        ) VALUES (
            OLD."FormId", v_action_type, row_to_json(OLD), 
            NULL, v_changed_by, NOW()
        );
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMIT;
