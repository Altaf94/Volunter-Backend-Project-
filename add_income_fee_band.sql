CREATE TABLE IF NOT EXISTS "IncomeFeeBand" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO "IncomeFeeBand" ("Name") VALUES
('0 – 1,000'),
('1,001 – 2,000'),
('2,001 – 4,000'),
('4,001 – 6,000'),
('6,001 – 8,000'),
('8,001 – 10,000'),
('10,001 – 15,000'),
('15,001 – 20,000'),
('20,001 – 30,000'),
('30,001 – 50,000'),
('50,001 and above')
ON CONFLICT ("Name") DO NOTHING;

ALTER TABLE "FamilyLevelDetails"
ADD COLUMN IF NOT EXISTS "IncomeFeeBandId" INTEGER REFERENCES "IncomeFeeBand"("Id");

COMMENT ON COLUMN "FamilyLevelDetails"."IncomeFeeBandId" IS 'Family member income fee band reference';

COMMIT;
