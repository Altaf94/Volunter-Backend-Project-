-- Add IsBank column to FamilyLevelDetails table
-- This script adds the IsBank boolean field to the FamilyLevelDetails table

ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN "IsBank" BOOLEAN DEFAULT NULL;

-- Add comment to describe the column
COMMENT ON COLUMN "FamilyLevelDetails"."IsBank" IS 'Bank status (yes/no) for family member';
