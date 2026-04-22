-- Initialize JamatKhana Database
-- This script creates the necessary tables and inserts initial data

-- Create tables
CREATE TABLE IF NOT EXISTS "Role" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "User_Status" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "RegionalCouncil" (
    "Id" VARCHAR(50) PRIMARY KEY,
    "Code" INTEGER NOT NULL,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "LocalCouncil" (
    "Id" VARCHAR(50) PRIMARY KEY,
    "Code" INTEGER NOT NULL,
    "Name" VARCHAR(100) NOT NULL,
    "RegionalCouncilId" VARCHAR(50) REFERENCES "RegionalCouncil"("Id")
);

CREATE TABLE IF NOT EXISTS "JamatKhana" (
    "Id" VARCHAR(50) PRIMARY KEY,
    "Code" VARCHAR(20) NOT NULL,
    "Name" VARCHAR(100) NOT NULL,
    "LocalCouncilId" VARCHAR(50) REFERENCES "LocalCouncil"("Id")
);

CREATE TABLE IF NOT EXISTS "User" (
    "Id" VARCHAR(50) PRIMARY KEY,
    "Email" VARCHAR(100) UNIQUE NOT NULL,
    "FullName" VARCHAR(100) NOT NULL,
    "PhoneNumber" VARCHAR(20),
    "PasswordHash" VARCHAR(256),
    "RoleId" INTEGER REFERENCES "Role"("Id"),
    "StatusId" INTEGER REFERENCES "User_Status"("Id"),
    "JamatKhanaIds" VARCHAR(50)[], -- Array of JamatKhana IDs
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "UpdatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "IsActive" BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS "FormStatus" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "RejectReason" (
    "Id" SERIAL PRIMARY KEY,
    "Reason" VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS "FamilyIncomeStatus" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

-- New lookup tables for family member details
CREATE TABLE IF NOT EXISTS "IdType" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "Gender" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS "RelationshipToHead" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "MaritalStatus" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS "NotStudyingReason" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "SchoolType" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "OccupationType" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "NoEarningReason" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "EarningType" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS "EmploymentType" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS "IncomeBand" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "BankType" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "Level" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "Grade" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "ExaminationBoard" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "Stream" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS "University" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS "UniversityMode" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "Sector" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS "Form" (
    "FormId" VARCHAR(50) PRIMARY KEY,
    "EnumeratorId" VARCHAR(50) REFERENCES "User"("Id"),
    "JamatKhanaId" VARCHAR(50) REFERENCES "JamatKhana"("Id"),
    "HouseHoldCNIC" VARCHAR(20),
    "HouseOwnership" BOOLEAN, -- true/false for house ownership
    "IsWeb" BOOLEAN,
    "FamilyIncomeSourcesIds" INTEGER[], -- Array of FamilyIncomeStatus IDs for multi-select income sources
    "IncomeBandId" INTEGER REFERENCES "IncomeBand"("Id"), -- Family income band reference
    "FamilyMembersInPakistan" INTEGER, -- Number of family members living elsewhere in Pakistan
    "FamilyMembersOutsidePakistan" INTEGER, -- Number of family members living outside Pakistan
    "FamilyMembersCNICInPakistan" VARCHAR(20)[], -- Array of CNIC/NICOP of family members living elsewhere in Pakistan
    "FormStatus" INTEGER REFERENCES "FormStatus"("Id") DEFAULT 1, -- 1=Pending, 2=Under Review, 3=Approved, 4=Rejected
    "RejectReasonId" INTEGER REFERENCES "RejectReason"("Id"),
    "RejectReasonText" VARCHAR(500),
    "RejectedBy" VARCHAR(50) REFERENCES "User"("Id"),
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "UpdatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "FamilyLevelDetails" (
    "Id" SERIAL PRIMARY KEY,
    "FormId" VARCHAR(50) REFERENCES "Form"("FormId") ON DELETE CASCADE,
    "IdTypeId" INTEGER REFERENCES "IdType"("Id"),
    "IdNumber" VARCHAR(20),
    "FullName" VARCHAR(100) NOT NULL,
    "GenderId" INTEGER REFERENCES "Gender"("Id"),
    "MonthYearOfBirth" VARCHAR(20),
    "MobileNumber" VARCHAR(20),
    "RelationshipToHeadId" INTEGER REFERENCES "RelationshipToHead"("Id"),
    "MaritalStatusId" INTEGER REFERENCES "MaritalStatus"("Id"),
    "CommunityAffiliation" BOOLEAN, -- true/false for community affiliation
    "IsStudying" BOOLEAN, -- true/false for studying status
    "NotStudyingReasonId" INTEGER REFERENCES "NotStudyingReason"("Id"), -- Reason for not studying
    "SchoolTypeId" INTEGER REFERENCES "SchoolType"("Id"), -- Type of school (AKES, Government, Private/NGO)
    "SchoolName" VARCHAR(200), -- Name of the school
    "LevelId" INTEGER REFERENCES "Level"("Id"), -- Education level reference
    "GradeId" INTEGER REFERENCES "Grade"("Id"), -- Grade level reference
    "ExaminationBoardId" INTEGER REFERENCES "ExaminationBoard"("Id"), -- Examination board reference
    "StreamId" INTEGER REFERENCES "Stream"("Id"), -- Stream reference
    "UniversityId" INTEGER REFERENCES "University"("Id"), -- University reference
    "UniversityModeId" INTEGER REFERENCES "UniversityMode"("Id"), -- University mode reference
    "SectorId" INTEGER REFERENCES "Sector"("Id"), -- Sector reference
    "Degree" VARCHAR(200), -- Degree name
    "TechnicalInstitutionName" VARCHAR(200), -- Technical institution name
    "TechnicalField" VARCHAR(200), -- Technical field
    "TechnicalDuration" VARCHAR(50), -- Technical duration in months
    "Fees" VARCHAR(100), -- Fee structure
    "BankAccount" VARCHAR(50), -- Bank account number
    "BankName" VARCHAR(100), -- Name of the bank
    "BankTypeId" INTEGER REFERENCES "BankType"("Id"), -- Bank type reference
    "HealthInsurance" BOOLEAN, -- Health insurance status (yes/no)
    "OccupationTypeId" INTEGER REFERENCES "OccupationType"("Id"), -- Type of occupation
    "EarningStatus" BOOLEAN, -- Earning status (yes/no)
    "NoEarningReasonId" INTEGER REFERENCES "NoEarningReason"("Id"), -- Reason for not earning
    "EarningTypeId" INTEGER REFERENCES "EarningType"("Id"), -- Type of earning (Individual or Family)
    "EmploymentTypeId" INTEGER REFERENCES "EmploymentType"("Id"), -- Type of employment (Employed, Business, Freelancer)
    "Industry" VARCHAR(100), -- Industry name
    "IncomeBandId" INTEGER REFERENCES "IncomeBand"("Id"), -- Income band reference
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "UpdatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial data
INSERT INTO "Role" ("Id", "Name") VALUES 
(1, 'Enumerator'),
(2, 'Checker'),
(3, 'Admin')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "User_Status" ("Id", "Name") VALUES 
(1, 'Active'),
(2, 'Inactive'),
(3, 'Suspended')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "FormStatus" ("Id", "Name") VALUES 
(1, 'Pending'),           -- Form is created but not yet reviewed
(2, 'Under Review'),      -- Form is being reviewed by checker
(3, 'Approved'),          -- Form has been approved
(4, 'Rejected')           -- Form has been rejected
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "RejectReason" ("Id", "Reason") VALUES 
(1, 'Incomplete Information'),
(2, 'Invalid Data'),
(3, 'Duplicate Entry'),
(4, 'Other')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "FamilyIncomeStatus" ("Id", "Name") VALUES 
(1, 'Agriculture'),
(2, 'Livestock'),
(3, 'Investment'),
(4, 'Business'),
(5, 'Salary'),
(6, 'Daily Wages'),
(7, 'Remittances'),
(8, 'Pensions'),
(9, 'Other')
ON CONFLICT ("Id") DO NOTHING;

-- Insert initial data for new lookup tables
INSERT INTO "IdType" ("Id", "Name") VALUES 
(1, 'CNIC'),
(2, 'NICOP')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "Gender" ("Id", "Name") VALUES 
(1, 'Male'),
(2, 'Female'),
(3, 'Other')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "RelationshipToHead" ("Id", "Name") VALUES 
(1, 'Head'),
(2, 'Spouse'),
(3, 'Son'),
(4, 'Daughter'),
(5, 'Father'),
(6, 'Mother'),
(7, 'Brother'),
(8, 'Sister'),
(9, 'Grandfather'),
(10, 'Grandmother'),
(11, 'Uncle'),
(12, 'Aunt'),
(13, 'Cousin'),
(14, 'Other')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "MaritalStatus" ("Id", "Name") VALUES 
(1, 'Single'),
(2, 'Married'),
(3, 'Widowed'),
(4, 'Divorced'),
(5, 'Separated')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "NotStudyingReason" ("Id", "Name") VALUES 
(1, 'Unemployed'),
(2, 'Student'),
(3, 'Homemaker'),
(4, 'Retired'),
(5, 'Disability/Health'),
(6, 'Other')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "SchoolType" ("Id", "Name") VALUES 
(1, 'AKES'),
(2, 'Government'),
(3, 'Private/NGO')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "OccupationType" ("Id", "Name") VALUES 
(1, 'Salaried'),
(2, 'Daily Wage Labor'),
(3, 'Passive Income (Stock, Remittance, Rental Income, Retired Pension)'),
(4, 'Self-employment/Business/Freelance/Home Based')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "NoEarningReason" ("Id", "Name") VALUES 
(1, 'Jobless'),
(2, 'Student'),
(3, 'Homemaker'),
(4, 'Retired'),
(5, 'Disability/Health'),
(6, 'Other')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "EarningType" ("Id", "Name") VALUES 
(1, 'Individual'),
(2, 'Family')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "EmploymentType" ("Id", "Name") VALUES 
(1, 'Employed'),
(2, 'Business'),
(3, 'Freelancer')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "IncomeBand" ("Id", "Name") VALUES 
(1, '10'),
(2, '20'),
(3, '30')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "BankType" ("Id", "Name") VALUES 
(1, 'Bank'),
(2, 'Cooperative Society')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "Level" ("Id", "Name") VALUES 
(1, 'School'),
(2, 'University'),
(3, 'Technical/Professional')
ON CONFLICT ("Id") DO NOTHING;

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

INSERT INTO "University" ("Id", "Name") VALUES 
(1, 'Aga Khan University'),
(2, 'Air University'),
(3, 'Al-Hamd Islamic University'),
(4, 'Bahauddin Zakariya University'),
(5, 'Baqai Medical University'),
(6, 'Barrett Hodgson University'),
(7, 'Beaconhouse National University'),
(8, 'Benazir Bhutto Shaheed University, Lyari'),
(9, 'Benazir Bhutto Shaheed University of Technology & Skill Development, Khairpur Mirs'),
(10, 'Cholistan University of Veterinary & Animal Sciences'),
(11, 'COMSATS University Islamabad'),
(12, 'Dawood University of Engineering & Technology'),
(13, 'Dow University of Health Sciences'),
(14, 'Emerson University, Multan'),
(15, 'Fatima Jinnah Medical University'),
(16, 'Fatima Jinnah Women University'),
(17, 'Forman Christian College University'),
(18, 'Government College University, Faisalabad'),
(19, 'Government College University, Hyderabad'),
(20, 'Government College University, Lahore'),
(21, 'Government College Women University, Sialkot'),
(22, 'Government Sadiq College Women University, Bahawalpur'),
(23, 'Government Viqar-un-Nisa Women University, Rawalpindi'),
(24, 'Green International University'),
(25, 'Habib University'),
(26, 'Hajvery University'),
(27, 'Hamdard University'),
(28, 'Indus Valley School of Art & Architecture'),
(29, 'Information Technology University (ITU), Lahore'),
(30, 'Institute of Business Administration (IBA), Karachi'),
(31, 'Institute for Art & Culture'),
(32, 'International Islamic University, Islamabad'),
(33, 'Karakoram International University, Gilgit'),
(34, 'King Edward Medical University'),
(35, 'Kinnaird College for Women University'),
(36, 'Lahore College for Women University'),
(37, 'Lahore Garrison University'),
(38, 'Lahore Institute of Science & Technology'),
(39, 'Lahore School of Economics'),
(40, 'Lahore University of Management Sciences (LUMS)'),
(41, 'Lasbela University of Agriculture, Water & Marine Sciences'),
(42, 'Minhaj University Lahore'),
(43, 'Mirpur University of Science & Technology'),
(44, 'Mohi-ud-Din Islamic University, Nerian Sharif'),
(45, 'Muhammad Nawaz Sharif University of Agriculture'),
(46, 'Muhammad Nawaz Sharif University of Engineering & Technology'),
(47, 'National College of Arts (NCA)'),
(48, 'National College of Business Administration & Economics (NCBA&E)'),
(49, 'National Defence University'),
(50, 'National Skills University, Islamabad'),
(51, 'National Textile University'),
(52, 'National University of Computer & Emerging Sciences (FAST-NUCES)'),
(53, 'National University of Medical Sciences (NUMS)'),
(54, 'National University of Modern Languages (NUML)'),
(55, 'National University of Sciences & Technology (NUST)'),
(56, 'NED University of Engineering & Technology'),
(57, 'NFC Institute of Engineering & Technology, Multan'),
(58, 'Nishtar Medical University'),
(59, 'NUR International University'),
(60, 'Pakistan Institute of Fashion & Design (PIFD)'),
(61, 'Pir Mehr Ali Shah Arid Agriculture University'),
(62, 'Punjab Tianjin University of Technology'),
(63, 'Qarshi University'),
(64, 'Quaid-i-Azam University'),
(65, 'Rashid Latif Khan University'),
(66, 'Rawalpindi Medical University'),
(67, 'Rawalpindi Women University'),
(68, 'Sardar Bahadur Khan Women University'),
(69, 'Shaheed Zulfikar Ali Bhutto Institute of Science & Technology (SZABIST)'),
(70, 'Sindh Agriculture University'),
(71, 'Sir Syed University of Engineering & Technology'),
(72, 'Sukkur IBA University'),
(73, 'Superior University'),
(74, 'Times Institute, Multan'),
(75, 'University of Agriculture, Faisalabad'),
(76, 'University of Azad Jammu & Kashmir'),
(77, 'University of Balochistan'),
(78, 'University of Central Punjab (UCP)'),
(79, 'University of Chenab, Gujrat'),
(80, 'University of Child Health Sciences'),
(81, 'University of Education'),
(82, 'University of Engineering & Technology, Lahore'),
(83, 'University of Engineering & Technology, Peshawar'),
(84, 'University of Gujrat'),
(85, 'University of Health Sciences, Lahore'),
(86, 'University of Karachi'),
(87, 'University of Kotli, AJK'),
(88, 'University of Lahore'),
(89, 'University of Loralai'),
(90, 'University of Management & Technology (UMT)'),
(91, 'University of Mirpurkhas'),
(92, 'University of Poonch, Rawalakot'),
(93, 'University of Sargodha'),
(94, 'University of Sialkot'),
(95, 'University of Sindh, Jamshoro'),
(96, 'University of South Asia'),
(97, 'University of Turbat'),
(98, 'University of Veterinary & Animal Sciences (UVAS), Lahore'),
(99, 'Women University Multan'),
(100, 'Women University of AJK, Bagh')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "UniversityMode" ("Id", "Name") VALUES 
(1, 'Online'),
(2, 'Hybrid'),
(3, 'Physical')
ON CONFLICT ("Id") DO NOTHING;

INSERT INTO "Sector" ("Id", "Name") VALUES 
(1, 'IT'),
(2, 'Finance'),
(3, 'Government'),
(4, 'Healthcare'),
(5, 'Education'),
(6, 'Manufacturing'),
(7, 'Construction'),
(8, 'Retail'),
(9, 'Transport')
ON CONFLICT ("Id") DO NOTHING;

-- Insert sample regional council
INSERT INTO "RegionalCouncil" ("Id", "Code", "Name") VALUES 
('RC001', 1, 'Sample Regional Council')
ON CONFLICT ("Id") DO NOTHING;

-- Insert sample local council
INSERT INTO "LocalCouncil" ("Id", "Code", "Name", "RegionalCouncilId") VALUES 
('LC001', 1, 'Sample Local Council', 'RC001')
ON CONFLICT ("Id") DO NOTHING;

-- Insert sample JamatKhana
INSERT INTO "JamatKhana" ("Id", "Code", "Name", "LocalCouncilId") VALUES 
('JK001', 'JK001', 'Sample JamatKhana', 'LC001')
ON CONFLICT ("Id") DO NOTHING;

-- Insert sample admin user (password: password123)
INSERT INTO "User" ("Id", "Email", "FullName", "PhoneNumber", "PasswordHash", "RoleId", "StatusId", "JamatKhanaIds") VALUES 
('ADMIN001', 'admin@example.com', 'System Administrator', '+1234567890', '$2b$12$6uO2t7GKgSVhj2NtFfNCbuTlJLVlKBHv7AaplQObwjX/QnoNBZ/7u', 3, 1, ARRAY['JK001'])
ON CONFLICT ("Id") DO NOTHING;

-- Insert sample enumerator user (password: password123)
INSERT INTO "User" ("Id", "Email", "FullName", "PhoneNumber", "PasswordHash", "RoleId", "StatusId", "JamatKhanaIds") VALUES 
('ENUM001', 'enumerator@example.com', 'John Doe - Enumerator', '+1234567891', '$2b$12$6uO2t7GKgSVhj2NtFfNCbuTlJLVlKBHv7AaplQObwjX/QnoNBZ/7u', 1, 1, ARRAY['JK001'])
ON CONFLICT ("Id") DO NOTHING;

-- Insert sample checker user (password: password123)
INSERT INTO "User" ("Id", "Email", "FullName", "PhoneNumber", "PasswordHash", "RoleId", "StatusId", "JamatKhanaIds") VALUES 
('CHECK001', 'checker@example.com', 'Jane Smith - Checker', '+1234567892', '$2b$12$6uO2t7GKgSVhj2NtFfNCbuTlJLVlKBHv7AaplQObwjX/QnoNBZ/7u', 2, 1, ARRAY['JK001'])
ON CONFLICT ("Id") DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_email ON "User"("Email");
CREATE INDEX IF NOT EXISTS idx_user_role ON "User"("RoleId");
-- Performance indexes for User common filters
CREATE INDEX IF NOT EXISTS idx_user_status ON "User"("StatusId");
CREATE INDEX IF NOT EXISTS idx_user_is_active ON "User"("IsActive");
CREATE INDEX IF NOT EXISTS idx_user_jk_ids ON "User" USING GIN ("JamatKhanaIds");
CREATE INDEX IF NOT EXISTS idx_form_enumerator ON "Form"("EnumeratorId");
CREATE INDEX IF NOT EXISTS idx_form_jamatkhana ON "Form"("JamatKhanaId");
CREATE INDEX IF NOT EXISTS idx_form_status ON "Form"("FormStatus");
CREATE INDEX IF NOT EXISTS idx_form_income_status ON "Form"("FamilyIncomeSourcesIds");
CREATE INDEX IF NOT EXISTS idx_form_family_income_sources_ids ON "Form" USING GIN ("FamilyIncomeSourcesIds");
CREATE INDEX IF NOT EXISTS idx_form_family_members_cnic ON "Form" USING GIN ("FamilyMembersCNICInPakistan");
-- Performance indexes for common GET filters/sorts
CREATE INDEX IF NOT EXISTS idx_form_created_at ON "Form"("CreatedAt");
CREATE INDEX IF NOT EXISTS idx_form_isweb ON "Form"("IsWeb");
CREATE INDEX IF NOT EXISTS idx_form_jk_created_at ON "Form"("JamatKhanaId", "CreatedAt");

-- Indexes for FamilyLevelDetails table
CREATE INDEX IF NOT EXISTS idx_family_details_form_id ON "FamilyLevelDetails"("FormId");
CREATE INDEX IF NOT EXISTS idx_family_details_id_type ON "FamilyLevelDetails"("IdTypeId");
CREATE INDEX IF NOT EXISTS idx_family_details_gender ON "FamilyLevelDetails"("GenderId");
CREATE INDEX IF NOT EXISTS idx_family_details_relationship ON "FamilyLevelDetails"("RelationshipToHeadId");
CREATE INDEX IF NOT EXISTS idx_family_details_marital_status ON "FamilyLevelDetails"("MaritalStatusId");
CREATE INDEX IF NOT EXISTS idx_family_details_not_studying_reason ON "FamilyLevelDetails"("NotStudyingReasonId");
CREATE INDEX IF NOT EXISTS idx_family_details_school_type ON "FamilyLevelDetails"("SchoolTypeId");
CREATE INDEX IF NOT EXISTS idx_family_details_occupation_type ON "FamilyLevelDetails"("OccupationTypeId");
CREATE INDEX IF NOT EXISTS idx_family_details_no_earning_reason ON "FamilyLevelDetails"("NoEarningReasonId");
CREATE INDEX IF NOT EXISTS idx_family_details_earning_type ON "FamilyLevelDetails"("EarningTypeId");
CREATE INDEX IF NOT EXISTS idx_family_details_employment_type ON "FamilyLevelDetails"("EmploymentTypeId");
CREATE INDEX IF NOT EXISTS idx_family_details_income_band ON "FamilyLevelDetails"("IncomeBandId");
CREATE INDEX IF NOT EXISTS idx_family_details_bank_type ON "FamilyLevelDetails"("BankTypeId");
CREATE INDEX IF NOT EXISTS idx_family_details_level ON "FamilyLevelDetails"("LevelId");
CREATE INDEX IF NOT EXISTS idx_family_details_grade ON "FamilyLevelDetails"("GradeId");
CREATE INDEX IF NOT EXISTS idx_family_details_examination_board ON "FamilyLevelDetails"("ExaminationBoardId");
CREATE INDEX IF NOT EXISTS idx_family_details_stream ON "FamilyLevelDetails"("StreamId");
CREATE INDEX IF NOT EXISTS idx_family_details_university ON "FamilyLevelDetails"("UniversityId");
CREATE INDEX IF NOT EXISTS idx_family_details_university_mode ON "FamilyLevelDetails"("UniversityModeId");
CREATE INDEX IF NOT EXISTS idx_family_details_sector ON "FamilyLevelDetails"("SectorId");
-- Performance indexes for FamilyLevelDetails common lookups
CREATE INDEX IF NOT EXISTS idx_fld_idnumber ON "FamilyLevelDetails"("IdNumber");
CREATE INDEX IF NOT EXISTS idx_fld_fullname ON "FamilyLevelDetails"("FullName");
CREATE INDEX IF NOT EXISTS idx_fld_mobilenumber ON "FamilyLevelDetails"("MobileNumber");

-- Lookup tables: Name/Code indexes to speed GET-all, filtering and ordering
CREATE INDEX IF NOT EXISTS idx_role_name ON "Role"("Name");
CREATE INDEX IF NOT EXISTS idx_user_status_name ON "User_Status"("Name");
CREATE INDEX IF NOT EXISTS idx_regional_council_code ON "RegionalCouncil"("Code");
CREATE INDEX IF NOT EXISTS idx_regional_council_name ON "RegionalCouncil"("Name");
CREATE INDEX IF NOT EXISTS idx_local_council_code ON "LocalCouncil"("Code");
CREATE INDEX IF NOT EXISTS idx_local_council_name ON "LocalCouncil"("Name");
CREATE INDEX IF NOT EXISTS idx_jk_code ON "JamatKhana"("Code");
CREATE INDEX IF NOT EXISTS idx_jk_name ON "JamatKhana"("Name");
CREATE INDEX IF NOT EXISTS idx_formstatus_name ON "FormStatus"("Name");
CREATE INDEX IF NOT EXISTS idx_rejectreason_name ON "RejectReason"("Reason");
CREATE INDEX IF NOT EXISTS idx_family_income_status_name ON "FamilyIncomeStatus"("Name");
CREATE INDEX IF NOT EXISTS idx_idtype_name ON "IdType"("Name");
CREATE INDEX IF NOT EXISTS idx_gender_name ON "Gender"("Name");
CREATE INDEX IF NOT EXISTS idx_relationshiptohead_name ON "RelationshipToHead"("Name");
CREATE INDEX IF NOT EXISTS idx_maritalstatus_name ON "MaritalStatus"("Name");
CREATE INDEX IF NOT EXISTS idx_not_studying_reason_name ON "NotStudyingReason"("Name");
CREATE INDEX IF NOT EXISTS idx_schooltype_name ON "SchoolType"("Name");
CREATE INDEX IF NOT EXISTS idx_occupationtype_name ON "OccupationType"("Name");
CREATE INDEX IF NOT EXISTS idx_noearningreason_name ON "NoEarningReason"("Name");
CREATE INDEX IF NOT EXISTS idx_earningtype_name ON "EarningType"("Name");
CREATE INDEX IF NOT EXISTS idx_employmenttype_name ON "EmploymentType"("Name");
CREATE INDEX IF NOT EXISTS idx_incomeband_name ON "IncomeBand"("Name");
CREATE INDEX IF NOT EXISTS idx_banktype_name ON "BankType"("Name");
CREATE INDEX IF NOT EXISTS idx_level_name ON "Level"("Name");
CREATE INDEX IF NOT EXISTS idx_grade_name ON "Grade"("Name");
CREATE INDEX IF NOT EXISTS idx_examinationboard_name ON "ExaminationBoard"("Name");
CREATE INDEX IF NOT EXISTS idx_stream_name ON "Stream"("Name");
CREATE INDEX IF NOT EXISTS idx_university_name ON "University"("Name");
CREATE INDEX IF NOT EXISTS idx_universitymode_name ON "UniversityMode"("Name");
CREATE INDEX IF NOT EXISTS idx_sector_name ON "Sector"("Name");

-- Foreign key helper indexes for faster joins
CREATE INDEX IF NOT EXISTS idx_local_council_regional_id ON "LocalCouncil"("RegionalCouncilId");
CREATE INDEX IF NOT EXISTS idx_jk_local_council_id ON "JamatKhana"("LocalCouncilId");

-- Add unique constraint for HouseHoldCNIC to prevent duplicate applications
ALTER TABLE "Form" ADD CONSTRAINT IF NOT EXISTS "uk_form_household_cnic" UNIQUE ("HouseHoldCNIC");

-- Add BankTypeId column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'BankTypeId'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "BankTypeId" INTEGER;
        ALTER TABLE "FamilyLevelDetails" ADD CONSTRAINT "fk_familyleveldetails_banktype" 
        FOREIGN KEY ("BankTypeId") REFERENCES "BankType"("Id");
    END IF;
END $$;

-- Add LevelId column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'LevelId'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "LevelId" INTEGER;
        ALTER TABLE "FamilyLevelDetails" ADD CONSTRAINT "fk_familyleveldetails_level" 
        FOREIGN KEY ("LevelId") REFERENCES "Level"("Id");
    END IF;
END $$;

-- Add GradeId column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'GradeId'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "GradeId" INTEGER;
        ALTER TABLE "FamilyLevelDetails" ADD CONSTRAINT "fk_familyleveldetails_grade" 
        FOREIGN KEY ("GradeId") REFERENCES "Grade"("Id");
    END IF;
END $$;

-- Add ExaminationBoardId column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'ExaminationBoardId'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "ExaminationBoardId" INTEGER;
        ALTER TABLE "FamilyLevelDetails" ADD CONSTRAINT "fk_familyleveldetails_examinationboard" 
        FOREIGN KEY ("ExaminationBoardId") REFERENCES "ExaminationBoard"("Id");
    END IF;
END $$;

-- Add StreamId column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'StreamId'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "StreamId" INTEGER;
        ALTER TABLE "FamilyLevelDetails" ADD CONSTRAINT "fk_familyleveldetails_stream" 
        FOREIGN KEY ("StreamId") REFERENCES "Stream"("Id");
    END IF;
END $$;

-- Add UniversityId column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'UniversityId'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "UniversityId" INTEGER;
        ALTER TABLE "FamilyLevelDetails" ADD CONSTRAINT "fk_familyleveldetails_university" 
        FOREIGN KEY ("UniversityId") REFERENCES "University"("Id");
    END IF;
END $$;

-- Add Degree column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'Degree'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "Degree" VARCHAR(200);
    END IF;
END $$;

-- Add UniversityModeId column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'UniversityModeId'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "UniversityModeId" INTEGER;
        ALTER TABLE "FamilyLevelDetails" ADD CONSTRAINT "fk_familyleveldetails_universitymode" 
        FOREIGN KEY ("UniversityModeId") REFERENCES "UniversityMode"("Id");
    END IF;
END $$;

-- Add SectorId column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'SectorId'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "SectorId" INTEGER;
        ALTER TABLE "FamilyLevelDetails" ADD CONSTRAINT "fk_familyleveldetails_sector" 
        FOREIGN KEY ("SectorId") REFERENCES "Sector"("Id");
    END IF;
END $$;

-- Add TechnicalInstitutionName column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'TechnicalInstitutionName'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "TechnicalInstitutionName" VARCHAR(200);
    END IF;
END $$;

-- Add TechnicalField column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'TechnicalField'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "TechnicalField" VARCHAR(200);
    END IF;
END $$;

-- Add TechnicalDuration column to existing FamilyLevelDetails table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'FamilyLevelDetails' 
        AND column_name = 'TechnicalDuration'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" ADD COLUMN "TechnicalDuration" VARCHAR(50);
    END IF;
END $$;

-- Add IncomeBandId column to existing Form table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'Form' 
        AND column_name = 'IncomeBandId'
    ) THEN
        ALTER TABLE "Form" ADD COLUMN "IncomeBandId" INTEGER;
        ALTER TABLE "Form" ADD CONSTRAINT "fk_form_incomeband" 
        FOREIGN KEY ("IncomeBandId") REFERENCES "IncomeBand"("Id");
    END IF;
END $$;

-- Add IsWeb column to existing Form table (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'Form' 
        AND column_name = 'IsWeb'
    ) THEN
        ALTER TABLE "Form" ADD COLUMN "IsWeb" BOOLEAN;
    END IF;
END $$;

-- Add column comments for documentation
COMMENT ON COLUMN "Form"."HouseOwnership" IS 'true/false for house ownership status';
COMMENT ON COLUMN "Form"."FamilyIncomeSourcesIds" IS 'Array of FamilyIncomeStatus IDs for multi-select income sources';
COMMENT ON COLUMN "Form"."IncomeBandId" IS 'Family income band reference';
COMMENT ON COLUMN "Form"."FamilyMembersInPakistan" IS 'Number of family members living elsewhere in Pakistan';
COMMENT ON COLUMN "Form"."FamilyMembersOutsidePakistan" IS 'Number of family members living outside Pakistan';
COMMENT ON COLUMN "Form"."FamilyMembersCNICInPakistan" IS 'Array of CNIC/NICOP of family members living elsewhere in Pakistan';
COMMENT ON COLUMN "FamilyLevelDetails"."CommunityAffiliation" IS 'true/false for community affiliation status';
COMMENT ON COLUMN "FamilyLevelDetails"."IsStudying" IS 'true/false for studying status';
COMMENT ON COLUMN "FamilyLevelDetails"."NotStudyingReasonId" IS 'Reason for not studying (reference to NotStudyingReason table)';
COMMENT ON COLUMN "FamilyLevelDetails"."SchoolTypeId" IS 'Type of school (reference to SchoolType table)';
COMMENT ON COLUMN "FamilyLevelDetails"."SchoolName" IS 'Name of the school';
COMMENT ON COLUMN "FamilyLevelDetails"."LevelId" IS 'Education level reference (School, University, Technical/Professional)';
COMMENT ON COLUMN "FamilyLevelDetails"."GradeId" IS 'Grade level reference (ECD, Grade 1-12, O Levels, A Levels)';
COMMENT ON COLUMN "FamilyLevelDetails"."ExaminationBoardId" IS 'Examination board reference (Federal, Punjab, Sindh, etc.)';
COMMENT ON COLUMN "FamilyLevelDetails"."StreamId" IS 'Stream reference (Science, Computer Science, Arts, etc.)';
COMMENT ON COLUMN "FamilyLevelDetails"."UniversityId" IS 'University reference (Aga Khan University, LUMS, etc.)';
COMMENT ON COLUMN "FamilyLevelDetails"."UniversityModeId" IS 'University mode reference (Online, Hybrid, Physical)';
COMMENT ON COLUMN "FamilyLevelDetails"."SectorId" IS 'Sector reference (IT, Finance, Government, Healthcare, Education, Manufacturing, Construction, Retail, Transport)';
COMMENT ON COLUMN "FamilyLevelDetails"."Degree" IS 'Degree name (Bachelor of Science, Master of Arts, etc.)';
COMMENT ON COLUMN "FamilyLevelDetails"."TechnicalInstitutionName" IS 'Technical institution name';
COMMENT ON COLUMN "FamilyLevelDetails"."TechnicalField" IS 'Technical field of study';
COMMENT ON COLUMN "FamilyLevelDetails"."TechnicalDuration" IS 'Technical course duration in months';
COMMENT ON COLUMN "FamilyLevelDetails"."Fees" IS 'Fee structure';
COMMENT ON COLUMN "FamilyLevelDetails"."BankAccount" IS 'Bank account number';
COMMENT ON COLUMN "FamilyLevelDetails"."BankName" IS 'Name of the bank';
COMMENT ON COLUMN "FamilyLevelDetails"."BankTypeId" IS 'Bank type reference (Commercial, Islamic, Microfinance, etc.)';
COMMENT ON COLUMN "FamilyLevelDetails"."HealthInsurance" IS 'Health insurance status (yes/no)';
COMMENT ON COLUMN "FamilyLevelDetails"."OccupationTypeId" IS 'Type of occupation (reference to OccupationType table)';
COMMENT ON COLUMN "FamilyLevelDetails"."EarningStatus" IS 'Earning status (yes/no)';
COMMENT ON COLUMN "FamilyLevelDetails"."NoEarningReasonId" IS 'Reason for not earning (reference to NoEarningReason table)';
COMMENT ON COLUMN "FamilyLevelDetails"."EarningTypeId" IS 'Type of earning (Individual or Family)';
COMMENT ON COLUMN "FamilyLevelDetails"."EmploymentTypeId" IS 'Type of employment (Employed, Business, Freelancer)';
COMMENT ON COLUMN "FamilyLevelDetails"."Industry" IS 'Industry name';
COMMENT ON COLUMN "FamilyLevelDetails"."IncomeBandId" IS 'Income band reference (10, 20, 30)';

COMMENT ON COLUMN "FamilyLevelDetails"."FormId" IS 'Reference to the main Form record';
COMMENT ON COLUMN "FamilyLevelDetails"."IdTypeId" IS 'Type of ID (CNIC/NICOP)';
COMMENT ON COLUMN "FamilyLevelDetails"."IdNumber" IS 'CNIC/NICOP number';
COMMENT ON COLUMN "FamilyLevelDetails"."FullName" IS 'Full name of family member';
COMMENT ON COLUMN "FamilyLevelDetails"."GenderId" IS 'Gender of family member';
COMMENT ON COLUMN "FamilyLevelDetails"."MonthYearOfBirth" IS 'Month and year of birth (format: MM-YYYY)';
COMMENT ON COLUMN "FamilyLevelDetails"."MobileNumber" IS 'Mobile phone number';
COMMENT ON COLUMN "FamilyLevelDetails"."RelationshipToHeadId" IS 'Relationship to household head';
COMMENT ON COLUMN "FamilyLevelDetails"."MaritalStatusId" IS 'Current marital status';
