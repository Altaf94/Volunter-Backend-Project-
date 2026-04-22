-- Migration script to add StreamId column to FamilyLevelDetails table
-- Run this script to add the missing StreamId column

-- First, ensure the Stream table exists
CREATE TABLE IF NOT EXISTS "Stream" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

-- Insert the stream data
INSERT INTO "Stream" ("Id", "Name") VALUES 
(1, 'Science'),
(2, 'Computer Science'),
(3, 'Arts / Humanities'),
(4, 'Pre-Medical'),
(5, 'Pre-Engineering'),
(6, 'Commerce'),
(7, 'General Science'),
(8, 'Home Economics')
ON CONFLICT ("Id") DO NOTHING;

-- Add the StreamId column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "StreamId" INTEGER;

-- Add foreign key constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_familyleveldetails_stream'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" 
        ADD CONSTRAINT "fk_familyleveldetails_stream" 
        FOREIGN KEY ("StreamId") REFERENCES "Stream"("Id");
    END IF;
END $$;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS "idx_familyleveldetails_streamid" 
ON "FamilyLevelDetails"("StreamId");

COMMIT;
