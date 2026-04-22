-- Migration script to add UniversityModeId column to FamilyLevelDetails table
-- Run this script to add the missing UniversityModeId column

-- First, ensure the UniversityMode table exists
CREATE TABLE IF NOT EXISTS "UniversityMode" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

-- Insert the university mode data
INSERT INTO "UniversityMode" ("Id", "Name") VALUES 
(1, 'Online'),
(2, 'Hybrid'),
(3, 'Physical')
ON CONFLICT ("Id") DO NOTHING;

-- Add the UniversityModeId column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "UniversityModeId" INTEGER;

-- Add foreign key constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_familyleveldetails_universitymode'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" 
        ADD CONSTRAINT "fk_familyleveldetails_universitymode" 
        FOREIGN KEY ("UniversityModeId") REFERENCES "UniversityMode"("Id");
    END IF;
END $$;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS "idx_familyleveldetails_universitymodeid" 
ON "FamilyLevelDetails"("UniversityModeId");

COMMIT;
