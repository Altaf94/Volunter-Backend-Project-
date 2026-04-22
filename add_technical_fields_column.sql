-- Migration script to add Technical fields to FamilyLevelDetails table
-- Run this script to add the missing Technical fields

-- Add the TechnicalInstitutionName column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "TechnicalInstitutionName" VARCHAR(200);

-- Add the TechnicalField column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "TechnicalField" VARCHAR(200);

-- Add the TechnicalDuration column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "TechnicalDuration" VARCHAR(50);

-- Add column comments for documentation
COMMENT ON COLUMN "FamilyLevelDetails"."TechnicalInstitutionName" IS 'Technical institution name';
COMMENT ON COLUMN "FamilyLevelDetails"."TechnicalField" IS 'Technical field of study';
COMMENT ON COLUMN "FamilyLevelDetails"."TechnicalDuration" IS 'Technical course duration in months';

COMMIT;
