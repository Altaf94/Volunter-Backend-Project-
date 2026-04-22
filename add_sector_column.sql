-- Migration script to add Sector table and SectorId column to FamilyLevelDetails table
-- Run this script to add the missing Sector functionality

-- Create Sector table if it doesn't exist
CREATE TABLE IF NOT EXISTS "Sector" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL UNIQUE
);

-- Insert Sector data
INSERT INTO "Sector" ("Id", "Name") VALUES 
(1, 'IT'),
(2, 'Finance'),
(3, 'Government'),
(4, 'Healthcare'),
(5, 'Education'),
(6, 'Manufacturing'),
(7, 'Construction'),
(8, 'Retail'),
(9, 'Transport')
ON CONFLICT ("Id") DO NOTHING;

-- Add the SectorId column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "SectorId" INTEGER;

-- Add foreign key constraint
ALTER TABLE "FamilyLevelDetails" 
ADD CONSTRAINT IF NOT EXISTS "fk_familyleveldetails_sector" 
FOREIGN KEY ("SectorId") REFERENCES "Sector"("Id");

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_family_details_sector ON "FamilyLevelDetails"("SectorId");

-- Add column comment for documentation
COMMENT ON COLUMN "FamilyLevelDetails"."SectorId" IS 'Sector reference (IT, Finance, Government, Healthcare, Education, Manufacturing, Construction, Retail, Transport)';

COMMIT;
