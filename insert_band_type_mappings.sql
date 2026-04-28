-- ============================================
-- INSERT BAND TYPE ACCESS LEVEL DUTY TYPE MAPPINGS
-- Maps access_level_id to band_type_id (1:1 correspondence)
-- Each access level gets its corresponding band type for all duty types
-- ============================================

INSERT INTO band_type_access_level_duty_type (band_type_id, access_level_id, duty_type_id, created_at)
SELECT 
    al.id as band_type_id,
    al.id as access_level_id,
    dt.id as duty_type_id,
    NOW() as created_at
FROM access_levels al
CROSS JOIN duty_types dt
WHERE al.is_active = true
  AND dt.is_active = true
  AND dt.name <> 'All'
ON CONFLICT (band_type_id, access_level_id, duty_type_id) DO NOTHING;

-- Verify the mapping
SELECT COUNT(*) as total_mappings FROM band_type_access_level_duty_type;

-- Show sample mappings
SELECT 
    btact.id,
    bt.name as band_type,
    al.name as access_level,
    dt.name as duty_type,
    btact.created_at
FROM band_type_access_level_duty_type btact
JOIN band_types bt ON btact.band_type_id = bt.id
JOIN access_levels al ON btact.access_level_id = al.id
JOIN duty_types dt ON btact.duty_type_id = dt.id
ORDER BY btact.band_type_id, btact.duty_type_id
LIMIT 20;
