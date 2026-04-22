-- Migration script to add LevelId column to FamilyLevelDetails table
-- Run this script to add the missing LevelId column

-- First, ensure the Level table exists
CREATE TABLE IF NOT EXISTS "Level" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

-- Insert the level data
INSERT INTO "Level" ("Id", "Name") VALUES 
(1, 'School'),
(2, 'University'),
(3, 'Technical/Professional')
ON CONFLICT ("Id") DO NOTHING;

-- Add the LevelId column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "LevelId" INTEGER;

-- Add foreign key constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_familyleveldetails_level'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" 
        ADD CONSTRAINT "fk_familyleveldetails_level" 
        FOREIGN KEY ("LevelId") REFERENCES "Level"("Id");
    END IF;
END $$;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS "idx_familyleveldetails_levelid" 
ON "FamilyLevelDetails"("LevelId");

COMMIT;
