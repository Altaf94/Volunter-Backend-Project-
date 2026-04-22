CREATE TABLE IF NOT EXISTS "FamilyLevelDetailsAudit" (
    "Id" BIGSERIAL PRIMARY KEY,
    "FamilyLevelDetailsId" BIGINT,
    "FormId" VARCHAR(50),
    "Action" VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    "OldData" JSONB,
    "NewData" JSONB,
    "ChangedBy" VARCHAR(50), -- optional: app can set via session variable later
    "ChangedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION fn_family_level_details_audit() RETURNS TRIGGER AS $$
DECLARE
    v_changed_by TEXT;
BEGIN
    -- Optionally pull from a session variable if the app sets it:
    BEGIN
        v_changed_by := current_setting('application.user_id', true);
    EXCEPTION WHEN others THEN
        v_changed_by := NULL;
    END;

    IF (TG_OP = 'INSERT') THEN
        INSERT INTO "FamilyLevelDetailsAudit" ("FamilyLevelDetailsId", "FormId", "Action", "OldData", "NewData", "ChangedBy")
        VALUES (NEW."Id", NEW."FormId", 'INSERT', NULL, to_jsonb(NEW), v_changed_by);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO "FamilyLevelDetailsAudit" ("FamilyLevelDetailsId", "FormId", "Action", "OldData", "NewData", "ChangedBy")
        VALUES (NEW."Id", NEW."FormId", 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), v_changed_by);
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO "FamilyLevelDetailsAudit" ("FamilyLevelDetailsId", "FormId", "Action", "OldData", "NewData", "ChangedBy")
        VALUES (OLD."Id", OLD."FormId", 'DELETE', to_jsonb(OLD), NULL, v_changed_by);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_family_level_details_audit_insert ON "FamilyLevelDetails";
DROP TRIGGER IF EXISTS trg_family_level_details_audit_update ON "FamilyLevelDetails";
DROP TRIGGER IF EXISTS trg_family_level_details_audit_delete ON "FamilyLevelDetails";

CREATE TRIGGER trg_family_level_details_audit_insert
AFTER INSERT ON "FamilyLevelDetails"
FOR EACH ROW EXECUTE FUNCTION fn_family_level_details_audit();

CREATE TRIGGER trg_family_level_details_audit_update
AFTER UPDATE ON "FamilyLevelDetails"
FOR EACH ROW EXECUTE FUNCTION fn_family_level_details_audit();

CREATE TRIGGER trg_family_level_details_audit_delete
AFTER DELETE ON "FamilyLevelDetails"
FOR EACH ROW EXECUTE FUNCTION fn_family_level_details_audit();

COMMENT ON TABLE "FamilyLevelDetailsAudit" IS 'Audit trail for FamilyLevelDetails row-level changes.';

COMMIT;
