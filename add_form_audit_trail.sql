CREATE TABLE IF NOT EXISTS "FormAudit" (
    "Id" BIGSERIAL PRIMARY KEY,
    "FormId" VARCHAR(50),
    "Action" VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    "OldData" JSONB,
    "NewData" JSONB,
    "ChangedBy" VARCHAR(50), -- optional: app can set via session variable later
    "ChangedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
        INSERT INTO "FormAudit" ("FormId", "Action", "OldData", "NewData", "ChangedBy")
        VALUES (NEW."FormId", 'INSERT', NULL, to_jsonb(NEW), v_changed_by);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO "FormAudit" ("FormId", "Action", "OldData", "NewData", "ChangedBy")
        VALUES (NEW."FormId", 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), v_changed_by);
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO "FormAudit" ("FormId", "Action", "OldData", "NewData", "ChangedBy")
        VALUES (OLD."FormId", 'DELETE', to_jsonb(OLD), NULL, v_changed_by);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_form_audit_insert ON "Form";
DROP TRIGGER IF EXISTS trg_form_audit_update ON "Form";
DROP TRIGGER IF EXISTS trg_form_audit_delete ON "Form";

CREATE TRIGGER trg_form_audit_insert
AFTER INSERT ON "Form"
FOR EACH ROW EXECUTE FUNCTION fn_form_audit();

CREATE TRIGGER trg_form_audit_update
AFTER UPDATE ON "Form"
FOR EACH ROW EXECUTE FUNCTION fn_form_audit();

CREATE TRIGGER trg_form_audit_delete
AFTER DELETE ON "Form"
FOR EACH ROW EXECUTE FUNCTION fn_form_audit();

COMMENT ON TABLE "FormAudit" IS 'Audit trail for Form row-level changes.';

COMMIT;
