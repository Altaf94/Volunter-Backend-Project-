-- Speed up GET/POST by checker_id (e.g. /api/volunteers/by-import-or-user)
-- Run against Heroku/Postgres: psql $DATABASE_URL -f add_index_volunteer_record_checker_id.sql
CREATE INDEX IF NOT EXISTS idx_volunteer_record_checker_id
    ON volunteer_record (checker_id);
