-- Migration script to add ExaminationBoardId column to FamilyLevelDetails table
-- Run this script to add the missing ExaminationBoardId column

-- First, ensure the ExaminationBoard table exists
CREATE TABLE IF NOT EXISTS "ExaminationBoard" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

-- Insert the examination board data
INSERT INTO "ExaminationBoard" ("Id", "Name") VALUES 
(1, 'Federal'),
(2, 'Punjab'),
(3, 'Sindh'),
(4, 'Khyber Pakhtunkhwa'),
(5, 'Balochistan'),
(6, 'AJK'),
(7, 'AKUEB (Aga Khan University Examination Board)'),
(8, 'Technical Education'),
(9, 'Religious'),
(10, 'International')
ON CONFLICT ("Id") DO NOTHING;

-- Add the ExaminationBoardId column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "ExaminationBoardId" INTEGER;

-- Add foreign key constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_familyleveldetails_examinationboard'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" 
        ADD CONSTRAINT "fk_familyleveldetails_examinationboard" 
        FOREIGN KEY ("ExaminationBoardId") REFERENCES "ExaminationBoard"("Id");
    END IF;
END $$;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS "idx_familyleveldetails_examinationboardid" 
ON "FamilyLevelDetails"("ExaminationBoardId");

COMMIT;
