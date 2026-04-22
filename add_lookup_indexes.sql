CREATE INDEX IF NOT EXISTS idx_familyincomestatus_name ON "FamilyIncomeStatus" ("Name");
CREATE INDEX IF NOT EXISTS idx_idtype_name ON "IdType" ("Name");
CREATE INDEX IF NOT EXISTS idx_gender_name ON "Gender" ("Name");
CREATE INDEX IF NOT EXISTS idx_relationshiptohead_name ON "RelationshipToHead" ("Name");
CREATE INDEX IF NOT EXISTS idx_maritalstatus_name ON "MaritalStatus" ("Name");
CREATE INDEX IF NOT EXISTS idx_notstudyingreason_name ON "NotStudyingReason" ("Name");
CREATE INDEX IF NOT EXISTS idx_schooltype_name ON "SchoolType" ("Name");
CREATE INDEX IF NOT EXISTS idx_occupationtype_name ON "OccupationType" ("Name");
CREATE INDEX IF NOT EXISTS idx_noearningreason_name ON "NoEarningReason" ("Name");
CREATE INDEX IF NOT EXISTS idx_earningtype_name ON "EarningType" ("Name");
CREATE INDEX IF NOT EXISTS idx_employmenttype_name ON "EmploymentType" ("Name");
CREATE INDEX IF NOT EXISTS idx_incomeband_name ON "IncomeBand" ("Name");
CREATE INDEX IF NOT EXISTS idx_banktype_name ON "BankType" ("Name");
CREATE INDEX IF NOT EXISTS idx_level_name ON "Level" ("Name");
CREATE INDEX IF NOT EXISTS idx_grade_name ON "Grade" ("Name");
CREATE INDEX IF NOT EXISTS idx_examinationboard_name ON "ExaminationBoard" ("Name");
CREATE INDEX IF NOT EXISTS idx_stream_name ON "Stream" ("Name");
CREATE INDEX IF NOT EXISTS idx_university_name ON "University" ("Name");
CREATE INDEX IF NOT EXISTS idx_universitymode_name ON "UniversityMode" ("Name");
CREATE INDEX IF NOT EXISTS idx_sector_name ON "Sector" ("Name");
CREATE INDEX IF NOT EXISTS idx_degree_name ON "Degree" ("Name");

-- HighestQualification
CREATE INDEX IF NOT EXISTS idx_highestqualification_name ON "HighestQualification" ("Name");

-- IncomeFeeBand
CREATE INDEX IF NOT EXISTS idx_incomefeeband_name ON "IncomeFeeBand" ("Name");

-- FormStatus
CREATE INDEX IF NOT EXISTS idx_formstatus_name ON "FormStatus" ("Name");

-- RejectReason
CREATE INDEX IF NOT EXISTS idx_rejectreason_reason ON "RejectReason" ("Reason");

-- UserRole
CREATE INDEX IF NOT EXISTS idx_userrole_name ON "UserRole" ("Name");

-- UserStatus
CREATE INDEX IF NOT EXISTS idx_userstatus_name ON "User_Status" ("Name");

-- RegionalCouncil
CREATE INDEX IF NOT EXISTS idx_regionalcouncil_name ON "RegionalCouncil" ("Name");

-- LocalCouncil
CREATE INDEX IF NOT EXISTS idx_localcouncil_name ON "LocalCouncil" ("Name");

-- JamatKhana
CREATE INDEX IF NOT EXISTS idx_jamatkhana_name ON "JamatKhana" ("Name");

COMMIT;
