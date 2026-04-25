-- ============================================
-- INSERT BAND TYPES
-- Band types correspond 1:1 to access levels by ID
-- ============================================

INSERT INTO band_types (id, name, is_active, created_at)
VALUES
(1, 'All', true, NOW()),
(2, 'Stage', true, NOW()),
(3, 'Health Area', true, NOW()),
(4, 'Pandal', true, NOW()),
(5, 'Holding Area', true, NOW()),
(6, 'Outside', true, NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- Verify insert
SELECT * FROM band_types ORDER BY id;
