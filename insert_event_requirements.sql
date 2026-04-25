-- ============================================
-- INSERT EVENT_ACCESS_LEVEL_DUTY_REQUIREMENTS
-- ============================================

INSERT INTO event_access_level_duty_requirements (event_id, access_level_id, duty_type_id, required_count, remaining) VALUES
-- Event 1: Gilgit
(1, 2, 1, 25, 5),     -- Stage + Reciter
(1, 2, 2, 30, 10),    -- Stage + Volunteer
(1, 3, 3, 15, 3),     -- Health Area + Doctor
(1, 3, 4, 20, 8),     -- Health Area + Nurse
(1, 4, 5, 35, 12),    -- Pandal + Red Carpet
(1, 4, 6, 20, 5),     -- Pandal + Medical Area
(1, 4, 7, 25, 8),     -- Pandal + Amaldar Area
(1, 4, 8, 40, 15),    -- Pandal + Pani Services
(1, 4, 9, 50, 20),    -- Pandal + Washroom
(1, 4, 10, 60, 25),   -- Pandal + Security
(1, 5, 11, 30, 10),   -- Holding Area + Access Control
(1, 5, 12, 25, 8),    -- Holding Area + Pani
(1, 5, 10, 45, 15),   -- Holding Area + Security
(1, 5, 9, 35, 12),    -- Holding Area + Washroom
(1, 6, 12, 20, 6),    -- Outside + Pani
(1, 6, 10, 40, 14),   -- Outside + Security
(1, 6, 13, 30, 10),   -- Outside + Transport

-- Event 2: Gupis - 1
(2, 2, 1, 28, 7),     -- Stage + Reciter
(2, 2, 2, 32, 11),    -- Stage + Volunteer
(2, 3, 3, 16, 4),     -- Health Area + Doctor
(2, 3, 4, 22, 9),     -- Health Area + Nurse
(2, 4, 5, 38, 13),    -- Pandal + Red Carpet
(2, 4, 6, 22, 6),     -- Pandal + Medical Area
(2, 4, 7, 26, 9),     -- Pandal + Amaldar Area
(2, 4, 8, 42, 16),    -- Pandal + Pani Services
(2, 4, 9, 52, 21),    -- Pandal + Washroom
(2, 4, 10, 62, 26),   -- Pandal + Security
(2, 5, 11, 32, 11),   -- Holding Area + Access Control
(2, 5, 12, 27, 9),    -- Holding Area + Pani
(2, 5, 10, 47, 16),   -- Holding Area + Security
(2, 5, 9, 37, 13),    -- Holding Area + Washroom
(2, 6, 12, 22, 7),    -- Outside + Pani
(2, 6, 10, 42, 15),   -- Outside + Security
(2, 6, 13, 32, 11),   -- Outside + Transport

-- Event 3: Gupis - 2
(3, 2, 1, 26, 6),     -- Stage + Reciter
(3, 2, 2, 31, 10),    -- Stage + Volunteer
(3, 3, 3, 14, 2),     -- Health Area + Doctor
(3, 3, 4, 21, 8),     -- Health Area + Nurse
(3, 4, 5, 36, 11),    -- Pandal + Red Carpet
(3, 4, 6, 21, 4),     -- Pandal + Medical Area
(3, 4, 7, 24, 7),     -- Pandal + Amaldar Area
(3, 4, 8, 41, 14),    -- Pandal + Pani Services
(3, 4, 9, 51, 19),    -- Pandal + Washroom
(3, 4, 10, 61, 24),   -- Pandal + Security
(3, 5, 11, 31, 9),    -- Holding Area + Access Control
(3, 5, 12, 26, 7),    -- Holding Area + Pani
(3, 5, 10, 46, 14),   -- Holding Area + Security
(3, 5, 9, 36, 11),    -- Holding Area + Washroom
(3, 6, 12, 21, 5),    -- Outside + Pani
(3, 6, 10, 41, 13),   -- Outside + Security
(3, 6, 13, 31, 9),    -- Outside + Transport

-- Event 4: Hunza
(4, 2, 1, 24, 4),     -- Stage + Reciter
(4, 2, 2, 29, 9),     -- Stage + Volunteer
(4, 3, 3, 13, 1),     -- Health Area + Doctor
(4, 3, 4, 19, 6),     -- Health Area + Nurse
(4, 4, 5, 34, 9),     -- Pandal + Red Carpet
(4, 4, 6, 19, 3),     -- Pandal + Medical Area
(4, 4, 7, 22, 5),     -- Pandal + Amaldar Area
(4, 4, 8, 39, 12),    -- Pandal + Pani Services
(4, 4, 9, 49, 17),    -- Pandal + Washroom
(4, 4, 10, 59, 22),   -- Pandal + Security
(4, 5, 11, 29, 7),    -- Holding Area + Access Control
(4, 5, 12, 24, 5),    -- Holding Area + Pani
(4, 5, 10, 44, 12),   -- Holding Area + Security
(4, 5, 9, 34, 9),     -- Holding Area + Washroom
(4, 6, 12, 19, 3),    -- Outside + Pani
(4, 6, 10, 39, 11),   -- Outside + Security
(4, 6, 13, 29, 7),    -- Outside + Transport

-- Event 5: Ishkoman - 1
(5, 2, 1, 27, 8),     -- Stage + Reciter
(5, 2, 2, 33, 12),    -- Stage + Volunteer
(5, 3, 3, 17, 5),     -- Health Area + Doctor
(5, 3, 4, 23, 10),    -- Health Area + Nurse
(5, 4, 5, 39, 14),    -- Pandal + Red Carpet
(5, 4, 6, 23, 7),     -- Pandal + Medical Area
(5, 4, 7, 27, 10),    -- Pandal + Amaldar Area
(5, 4, 8, 43, 17),    -- Pandal + Pani Services
(5, 4, 9, 53, 22),    -- Pandal + Washroom
(5, 4, 10, 63, 27),   -- Pandal + Security
(5, 5, 11, 33, 12),   -- Holding Area + Access Control
(5, 5, 12, 28, 10),   -- Holding Area + Pani
(5, 5, 10, 48, 17),   -- Holding Area + Security
(5, 5, 9, 38, 14),    -- Holding Area + Washroom
(5, 6, 12, 23, 8),    -- Outside + Pani
(5, 6, 10, 43, 16),   -- Outside + Security
(5, 6, 13, 33, 12),   -- Outside + Transport

-- Event 6: Ishkoman - 2
(6, 2, 1, 25, 5),     -- Stage + Reciter
(6, 2, 2, 30, 10),    -- Stage + Volunteer
(6, 3, 3, 15, 3),     -- Health Area + Doctor
(6, 3, 4, 20, 7),     -- Health Area + Nurse
(6, 4, 5, 35, 12),    -- Pandal + Red Carpet
(6, 4, 6, 20, 5),     -- Pandal + Medical Area
(6, 4, 7, 25, 8),     -- Pandal + Amaldar Area
(6, 4, 8, 40, 15),    -- Pandal + Pani Services
(6, 4, 9, 50, 20),    -- Pandal + Washroom
(6, 4, 10, 60, 25),   -- Pandal + Security
(6, 5, 11, 30, 10),   -- Holding Area + Access Control
(6, 5, 12, 25, 8),    -- Holding Area + Pani
(6, 5, 10, 45, 15),   -- Holding Area + Security
(6, 5, 9, 35, 12),    -- Holding Area + Washroom
(6, 6, 12, 20, 6),    -- Outside + Pani
(6, 6, 10, 40, 14),   -- Outside + Security
(6, 6, 13, 30, 10),   -- Outside + Transport

-- Event 7: Lower Chitral
(7, 2, 1, 23, 3),     -- Stage + Reciter
(7, 2, 2, 28, 8),     -- Stage + Volunteer
(7, 3, 3, 12, 0),     -- Health Area + Doctor
(7, 3, 4, 18, 5),     -- Health Area + Nurse
(7, 4, 5, 33, 8),     -- Pandal + Red Carpet
(7, 4, 6, 18, 2),     -- Pandal + Medical Area
(7, 4, 7, 23, 6),     -- Pandal + Amaldar Area
(7, 4, 8, 38, 13),    -- Pandal + Pani Services
(7, 4, 9, 48, 18),    -- Pandal + Washroom
(7, 4, 10, 58, 23),   -- Pandal + Security
(7, 5, 11, 28, 8),    -- Holding Area + Access Control
(7, 5, 12, 23, 6),    -- Holding Area + Pani
(7, 5, 10, 43, 13),   -- Holding Area + Security
(7, 5, 9, 33, 10),    -- Holding Area + Washroom
(7, 6, 12, 18, 4),    -- Outside + Pani
(7, 6, 10, 38, 12),   -- Outside + Security
(7, 6, 13, 28, 8),    -- Outside + Transport

-- Event 8: Upper Chitral - 1
(8, 2, 1, 29, 9),     -- Stage + Reciter
(8, 2, 2, 34, 13),    -- Stage + Volunteer
(8, 3, 3, 18, 6),     -- Health Area + Doctor
(8, 3, 4, 24, 11),    -- Health Area + Nurse
(8, 4, 5, 40, 15),    -- Pandal + Red Carpet
(8, 4, 6, 24, 8),     -- Pandal + Medical Area
(8, 4, 7, 28, 11),    -- Pandal + Amaldar Area
(8, 4, 8, 44, 18),    -- Pandal + Pani Services
(8, 4, 9, 54, 23),    -- Pandal + Washroom
(8, 4, 10, 64, 28),   -- Pandal + Security
(8, 5, 11, 34, 13),   -- Holding Area + Access Control
(8, 5, 12, 29, 11),   -- Holding Area + Pani
(8, 5, 10, 49, 18),   -- Holding Area + Security
(8, 5, 9, 39, 15),    -- Holding Area + Washroom
(8, 6, 12, 24, 9),    -- Outside + Pani
(8, 6, 10, 44, 17),   -- Outside + Security
(8, 6, 13, 34, 13),   -- Outside + Transport

-- Event 9: Upper Chitral - 2
(9, 2, 1, 26, 6),     -- Stage + Reciter
(9, 2, 2, 31, 11),    -- Stage + Volunteer
(9, 3, 3, 14, 2),     -- Health Area + Doctor
(9, 3, 4, 21, 8),     -- Health Area + Nurse
(9, 4, 5, 36, 11),    -- Pandal + Red Carpet
(9, 4, 6, 21, 4),     -- Pandal + Medical Area
(9, 4, 7, 25, 8),     -- Pandal + Amaldar Area
(9, 4, 8, 41, 15),    -- Pandal + Pani Services
(9, 4, 9, 51, 20),    -- Pandal + Washroom
(9, 4, 10, 61, 25),   -- Pandal + Security
(9, 5, 11, 31, 10),   -- Holding Area + Access Control
(9, 5, 12, 26, 8),    -- Holding Area + Pani
(9, 5, 10, 46, 15),   -- Holding Area + Security
(9, 5, 9, 36, 12),    -- Holding Area + Washroom
(9, 6, 12, 21, 6),    -- Outside + Pani
(9, 6, 10, 41, 14),   -- Outside + Security
(9, 6, 13, 31, 10)    -- Outside + Transport
ON CONFLICT DO NOTHING;
