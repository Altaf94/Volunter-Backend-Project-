-- Migration script to add UniversityId column to FamilyLevelDetails table
-- Run this script to add the missing UniversityId column

-- First, ensure the University table exists
CREATE TABLE IF NOT EXISTS "University" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(200) NOT NULL
);

-- Insert the university data
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

-- Add the UniversityId column to FamilyLevelDetails table
ALTER TABLE "FamilyLevelDetails" 
ADD COLUMN IF NOT EXISTS "UniversityId" INTEGER;

-- Add foreign key constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_familyleveldetails_university'
    ) THEN
        ALTER TABLE "FamilyLevelDetails" 
        ADD CONSTRAINT "fk_familyleveldetails_university" 
        FOREIGN KEY ("UniversityId") REFERENCES "University"("Id");
    END IF;
END $$;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS "idx_familyleveldetails_universityid" 
ON "FamilyLevelDetails"("UniversityId");

COMMIT;
