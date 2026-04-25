-- ============================================
-- INSERT EVENTS
-- ============================================

INSERT INTO events (id, name, is_active) VALUES
(1, 'Gilgit', true),
(2, 'Gupis - 1', true),
(3, 'Gupis - 2', true),
(4, 'Hunza', true),
(5, 'Ishkoman - 1', true),
(6, 'Ishkoman - 2', true),
(7, 'Lower Chitral', true),
(8, 'Upper Chitral - 1', true),
(9, 'Upper Chitral - 2', true)
ON CONFLICT (id) DO NOTHING;
