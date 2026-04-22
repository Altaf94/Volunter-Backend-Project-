ALTER TABLE "FamilyLevelDetails"
ADD COLUMN IF NOT EXISTS "AnyOtherSourceOfIncome" BOOLEAN,
ADD COLUMN IF NOT EXISTS "OtherIncomeSourceIds" INTEGER[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS "OtherIncomeBandId" INTEGER REFERENCES "IncomeBand"("Id");

COMMENT ON COLUMN "FamilyLevelDetails"."AnyOtherSourceOfIncome" IS 'Whether there are other income sources';
COMMENT ON COLUMN "FamilyLevelDetails"."OtherIncomeSourceIds" IS 'FamilyIncomeStatus Ids for other income sources';
COMMENT ON COLUMN "FamilyLevelDetails"."OtherIncomeBandId" IS 'IncomeBand Id for other income';

COMMIT;
