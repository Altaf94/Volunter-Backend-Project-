    -- Migration script to add Degree column to FamilyLevelDetails table
    -- Run this script to add the missing Degree column

    -- Add the Degree column to FamilyLevelDetails table
    -- Create Degree lookup table
    CREATE TABLE IF NOT EXISTS "Degree" (
        "Id" SERIAL PRIMARY KEY,
        "Name" VARCHAR(100) NOT NULL UNIQUE
    );

    -- Seed default degrees
    INSERT INTO "Degree" ("Name") VALUES
    ('Bachelors'),
    ('Masters(Postgraduate)'),
    ('M.Phil'),
    ('PHD')
    ON CONFLICT ("Name") DO NOTHING;

    -- Add DegreeId FK column to FamilyLevelDetails
    ALTER TABLE "FamilyLevelDetails" 
    ADD COLUMN IF NOT EXISTS "DegreeId" INTEGER REFERENCES "Degree"("Id");

-- Add HighestQualificationId FK column to FamilyLevelDetails (same options as Degree)
ALTER TABLE "FamilyLevelDetails"
ADD COLUMN IF NOT EXISTS "HighestQualificationId" INTEGER REFERENCES "Degree"("Id");

    -- Add column comment for documentation
COMMENT ON COLUMN "FamilyLevelDetails"."DegreeId" IS 'Degree reference (Bachelors, Masters(Postgraduate), M.Phil, PHD)';
COMMENT ON COLUMN "FamilyLevelDetails"."HighestQualificationId" IS 'Highest qualification reference (same as Degree options)';

    COMMIT;
