-- Migration script to add BankTypeId column to FamilyLevelDetails table
-- Run this script to add the missing BankTypeId column

-- First, ensure the BankType table exists
CREATE TABLE IF NOT EXISTS "BankType" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

-- Insert the bank type data
INSERT INTO "BankType" ("Id", "Name") VALUES 
(1, 'Bank'),
(2, 'Cooperative Society')
ON CONFLICT ("Id") DO NOTHING;

-- Add the BankTypeId column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "BankTypeId" INTEGER;

-- Add foreign key constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_familyleveldetails_banktype'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" 
        ADD CONSTRAINT "fk_familyleveldetails_banktype" 
        FOREIGN KEY ("BankTypeId") REFERENCES "BankType"("Id");
    END IF;
END $$;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS "idx_familyleveldetails_banktypeid" 
ON "FamilyLevelDetails"("BankTypeId");

COMMIT;
