-- Update IncomeBand table with new income ranges
-- This script will clear existing data and insert the new income band structure

-- Clear existing income band data
DELETE FROM "IncomeBand";

-- Insert new income band data
INSERT INTO "IncomeBand" ("Id", "Name") VALUES 
(1, '5,000 – 10,000 PKR'),
(2, '10,000 – 20,000 PKR'),
(3, '20,000 – 30,000 PKR'),
(4, '30,000 – 50,000 PKR'),
(5, '50,000 – 75,000 PKR'),
(6, '75,000 – 100,000 PKR'),
(7, '100,000 – 150,000 PKR'),
(8, '150,000 – 200,000 PKR'),
(9, '200,000 – 250,000 PKR'),
(10, '250,000 – 300,000 PKR'),
(11, 'Above 300,000 PKR'),
(12, 'Unknown / Not Disclosed');

-- Reset the sequence to start from 1
ALTER SEQUENCE "IncomeBand_Id_seq" RESTART WITH 13;

COMMIT;
