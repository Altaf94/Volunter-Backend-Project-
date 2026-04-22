-- Migration Script: Update from old form status system to simplified form status
-- Run this script if you have an existing database with the old schema

-- Step 1: Create the new FormStatus table
CREATE TABLE IF NOT EXISTS "FormStatus" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

-- Step 2: Insert the new form status values
INSERT INTO "FormStatus" ("Id", "Name") VALUES 
(1, 'Pending'),
(2, 'Under Review'),
(3, 'Approved'),
(4, 'Rejected')
ON CONFLICT ("Id") DO NOTHING;

-- Step 3: Add the new FormStatus column to the Form table
ALTER TABLE "Form" ADD COLUMN IF NOT EXISTS "FormStatus" INTEGER DEFAULT 1;

-- Step 4: Migrate existing data from old status fields to new FormStatus
-- This mapping assumes:
-- EnumeratorStatusId = 1 (Pending) -> FormStatus = 1 (Pending)
-- EnumeratorStatusId = 2 (In Progress) -> FormStatus = 1 (Pending)
-- EnumeratorStatusId = 3 (Completed) -> FormStatus = 2 (Under Review)
-- EnumeratorStatusId = 4 (Rejected) -> FormStatus = 4 (Rejected)
-- CheckerStatusId = 2 (Under Review) -> FormStatus = 2 (Under Review)
-- CheckerStatusId = 3 (Approved) -> FormStatus = 3 (Approved)
-- CheckerStatusId = 4 (Rejected) -> FormStatus = 4 (Rejected)

UPDATE "Form" 
SET "FormStatus" = CASE 
    WHEN "EnumeratorStatusId" = 3 THEN 2  -- Completed -> Under Review
    WHEN "EnumeratorStatusId" = 4 THEN 4  -- Rejected -> Rejected
    WHEN "CheckerStatusId" = 2 THEN 2     -- Under Review -> Under Review
    WHEN "CheckerStatusId" = 3 THEN 3     -- Approved -> Approved
    WHEN "CheckerStatusId" = 4 THEN 4     -- Rejected -> Rejected
    ELSE 1  -- Default to Pending
END
WHERE "FormStatus" = 1;  -- Only update records that still have default value

-- Step 5: Add foreign key constraint for FormStatus
ALTER TABLE "Form" ADD CONSTRAINT IF NOT EXISTS "fk_form_formstatus" 
    FOREIGN KEY ("FormStatus") REFERENCES "FormStatus"("Id");

-- Step 6: Update the index
DROP INDEX IF EXISTS idx_form_status;
CREATE INDEX IF NOT EXISTS idx_form_status ON "Form"("FormStatus");

-- Step 6.1: Add unique constraint for HouseHoldCNIC
ALTER TABLE "Form" ADD CONSTRAINT IF NOT EXISTS "uk_form_household_cnic" UNIQUE ("HouseHoldCNIC");

-- Step 7: Update FormData column to JSONB type
ALTER TABLE "Form" ALTER COLUMN "FormData" TYPE JSONB USING "FormData"::JSONB;

-- Step 8: Remove old columns (optional - uncomment if you want to clean up)
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "EnumeratorStatusId";
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "CheckerStatusId";
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "IsConflict";
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "IsRejected";
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "IsSubmitted";
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "IsSynced";
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "SyncError";
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "SyncRetryCount";
-- ALTER TABLE "Form" DROP COLUMN IF EXISTS "LastSyncAttempt";

-- Step 9: Drop old tables (optional - uncomment if you want to clean up)
-- DROP TABLE IF EXISTS "EnumeratorStatus";
-- DROP TABLE IF EXISTS "CheckerStatus";

-- Verification query - run this to check the migration
SELECT 
    f."FormId",
    f."FormStatus",
    fs."Name" as "StatusName",
    f."EnumeratorId",
    f."JamatKhanaId"
FROM "Form" f
JOIN "FormStatus" fs ON f."FormStatus" = fs."Id"
LIMIT 10;

-- Migration script to add missing form fields
-- Run this script to update your database schema

-- 1. Create FamilyIncomeStatus table
CREATE TABLE IF NOT EXISTS "FamilyIncomeStatus" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

-- 2. Insert initial FamilyIncomeStatus options
INSERT INTO "FamilyIncomeStatus" ("Name") VALUES 
    ('Agriculture'),
    ('Livestock'),
    ('Investment'),
    ('Business'),
    ('Salary'),
    ('Daily Wages'),
    ('Remittances'),
    ('Pensions'),
    ('Other')
ON CONFLICT DO NOTHING;

-- 3. Add new columns to Form table
ALTER TABLE "Form" 
ADD COLUMN IF NOT EXISTS "HouseOwnership" BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "FamilyIncomeStatusIds" INTEGER[] DEFAULT '{}';

-- 4. Create index on the new array column for better performance
CREATE INDEX IF NOT EXISTS idx_form_family_income_status_ids 
ON "Form" USING GIN ("FamilyIncomeStatusIds");

-- 5. Add comment to document the new fields
COMMENT ON COLUMN "Form"."HouseOwnership" IS 'true/false for house ownership status';
COMMENT ON COLUMN "Form"."FamilyIncomeStatusIds" IS 'Array of FamilyIncomeStatus IDs for multi-select income sources';
