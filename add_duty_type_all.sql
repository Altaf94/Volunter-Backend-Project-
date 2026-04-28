-- Add meta duty type "All" (UI / filters). Safe to re-run.
INSERT INTO duty_types (name, is_active) VALUES ('All', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Allow listing under the "All" access level only (not a station assignment)
INSERT INTO access_level_duty_types (access_level_id, duty_type_id)
SELECT al.id, dt.id
FROM access_levels al
CROSS JOIN duty_types dt
WHERE al.name = 'All' AND dt.name = 'All'
ON CONFLICT DO NOTHING;
