-- Migration script to add GradeId column to FamilyLevelDetails table
-- Run this script to add the missing GradeId column

-- First, ensure the Grade table exists
CREATE TABLE IF NOT EXISTS "Grade" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

-- Insert the grade data
INSERT INTO "Grade" ("Id", "Name") VALUES 
(1, 'ECD (Early Childhood Development)'),
(2, 'Grade 1'),
(3, 'Grade 2'),
(4, 'Grade 3'),
(5, 'Grade 4'),
(6, 'Grade 5'),
(7, 'Grade 6'),
(8, 'Grade 7'),
(9, 'Grade 8'),
(10, 'Grade 9'),
(11, 'Grade 10'),
(12, 'Grade 11'),
(13, 'Grade 12'),
(14, 'O Levels'),
(15, 'A Levels')
ON CONFLICT ("Id") DO NOTHING;

-- Add the GradeId column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "GradeId" INTEGER;

-- Add foreign key constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_familyleveldetails_grade'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" 
        ADD CONSTRAINT "fk_familyleveldetails_grade" 
        FOREIGN KEY ("GradeId") REFERENCES "Grade"("Id");
    END IF;
END $$;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS "idx_familyleveldetails_gradeid" 
ON "FamilyLevelDetails"("GradeId");

COMMIT;
