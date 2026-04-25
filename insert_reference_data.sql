-- ============================================
-- INSERT ACCESS LEVELS AND DUTY TYPES
-- ============================================

-- Insert Access Levels
INSERT INTO access_levels (name, is_active) VALUES
('All', true),
('Stage', true),
('Health Area', true),
('Pandal', true),
('Holding Area', true),
('Outside', true)
ON CONFLICT (name) DO NOTHING;

-- Insert Duty Types
INSERT INTO duty_types (name, is_active) VALUES
('Reciter', true),
('Volunteer', true),
('Doctor', true),
('Nurse', true),
('Red Carpet', true),
('Medical Area', true),
('Amaldar Area', true),
('Pani Services', true),
('Washroom', true),
('Security', true),
('Access Control', true),
('Pani', true),
('Transport', true)
ON CONFLICT (name) DO NOTHING;

-- Insert Access Level - Duty Type Mappings
INSERT INTO access_level_duty_types (access_level_id, duty_type_id) VALUES
((SELECT id FROM access_levels WHERE name='Stage'), (SELECT id FROM duty_types WHERE name='Reciter')),
((SELECT id FROM access_levels WHERE name='Stage'), (SELECT id FROM duty_types WHERE name='Volunteer')),
((SELECT id FROM access_levels WHERE name='Health Area'), (SELECT id FROM duty_types WHERE name='Doctor')),
((SELECT id FROM access_levels WHERE name='Health Area'), (SELECT id FROM duty_types WHERE name='Nurse')),
((SELECT id FROM access_levels WHERE name='Pandal'), (SELECT id FROM duty_types WHERE name='Red Carpet')),
((SELECT id FROM access_levels WHERE name='Pandal'), (SELECT id FROM duty_types WHERE name='Medical Area')),
((SELECT id FROM access_levels WHERE name='Pandal'), (SELECT id FROM duty_types WHERE name='Amaldar Area')),
((SELECT id FROM access_levels WHERE name='Pandal'), (SELECT id FROM duty_types WHERE name='Pani Services')),
((SELECT id FROM access_levels WHERE name='Pandal'), (SELECT id FROM duty_types WHERE name='Washroom')),
((SELECT id FROM access_levels WHERE name='Pandal'), (SELECT id FROM duty_types WHERE name='Security')),
((SELECT id FROM access_levels WHERE name='Holding Area'), (SELECT id FROM duty_types WHERE name='Access Control')),
((SELECT id FROM access_levels WHERE name='Holding Area'), (SELECT id FROM duty_types WHERE name='Pani')),
((SELECT id FROM access_levels WHERE name='Holding Area'), (SELECT id FROM duty_types WHERE name='Security')),
((SELECT id FROM access_levels WHERE name='Holding Area'), (SELECT id FROM duty_types WHERE name='Washroom')),
((SELECT id FROM access_levels WHERE name='Outside'), (SELECT id FROM duty_types WHERE name='Pani')),
((SELECT id FROM access_levels WHERE name='Outside'), (SELECT id FROM duty_types WHERE name='Security')),
((SELECT id FROM access_levels WHERE name='Outside'), (SELECT id FROM duty_types WHERE name='Transport'))
ON CONFLICT DO NOTHING;
