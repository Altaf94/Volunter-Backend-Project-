CREATE TABLE IF NOT EXISTS "HighestQualification" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO "HighestQualification" ("Name") VALUES
('Bachelors'),
('Masters(Postgraduate)'),
('M.Phil'),
('PHD')
ON CONFLICT ("Name") DO NOTHING;

-- Update the foreign key constraint for HighestQualificationId to point to HighestQualification instead of Degree
ALTER TABLE "FamilyLevelDetails" 
DROP CONSTRAINT IF EXISTS "FamilyLevelDetails_HighestQualificationId_fkey";

ALTER TABLE "FamilyLevelDetails" 
ADD CONSTRAINT "FamilyLevelDetails_HighestQualificationId_fkey" 
FOREIGN KEY ("HighestQualificationId") REFERENCES "HighestQualification"("Id");

COMMIT;
