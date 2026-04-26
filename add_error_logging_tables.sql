-- ============================================
-- ERROR LOGGING TABLES
-- Adds per-occurrence error_logs table and
-- seeds the error_codes registry.
--
-- Safe to run multiple times (idempotent).
-- ============================================

-- ---------- error_codes registry ----------
-- Column for HTTP code: many local DBs use `status` (not `http_status`).
-- If you only have `http_status` from an older dump, we rename it once.
-- Existing table shape we support:
--   id SERIAL PK
--   code VARCHAR(50) UNIQUE
--   status INTEGER          -- HTTP status (legacy name; keep as-is)
--   severity VARCHAR(20) DEFAULT 'error'
--   message VARCHAR(255)
--   details TEXT
--   created_at TIMESTAMP

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'error_codes' AND column_name = 'http_status'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'error_codes' AND column_name = 'status'
  ) THEN
    ALTER TABLE public.error_codes RENAME COLUMN http_status TO status;
  END IF;
END $$;

-- Make sure the registry exists (no-op if it already does)
CREATE TABLE IF NOT EXISTS error_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    status INTEGER,
    severity VARCHAR(20) NOT NULL DEFAULT 'error',
    message VARCHAR(255) NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------- error_logs (per-occurrence audit) ----------
CREATE TABLE IF NOT EXISTS error_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(64),
    error_code VARCHAR(50) NOT NULL,
    error_code_id INTEGER REFERENCES error_codes(id) ON DELETE SET NULL,
    http_status INTEGER,
    severity VARCHAR(20) NOT NULL DEFAULT 'error',
    message TEXT NOT NULL,
    details JSONB,
    user_id INTEGER,
    endpoint VARCHAR(255),
    http_method VARCHAR(10),
    client_ip VARCHAR(64),
    user_agent VARCHAR(512),
    stack_trace TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_code ON error_logs (error_code);
CREATE INDEX IF NOT EXISTS idx_error_logs_request_id ON error_logs (request_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs (severity);

-- ---------- Seed the error_codes registry ----------
-- Each error code gets a stable definition. UPSERT keeps the registry clean.
INSERT INTO error_codes (code, status, severity, message, details) VALUES
    -- Validation
    ('VALIDATION_ERROR',        400, 'error',    'Request validation failed',                   'Generic validation failure'),
    ('CNIC_INVALID',            400, 'warning',  'Invalid CNIC format',                         'CNIC must be 13 digits'),
    ('CNIC_NOT_FOUND',          400, 'warning',  'CNIC not found in enrollment database',       'CNIC was not located in census/enrollment data'),
    ('DUPLICATE_RECORD',        400, 'warning',  'Duplicate record',                            'A record with the same key already exists'),
    ('DISCREPANT_RECORD',       400, 'warning',  'Discrepant volunteer record',                 'Volunteer has conflicting duties / events'),
    ('INVALID_PAYLOAD',         400, 'error',    'Invalid request payload',                     'Body or query parameters could not be parsed'),
    ('MISSING_FIELD',           400, 'error',    'Required field missing',                      'A mandatory field was not provided'),

    -- Authentication / Authorization
    ('UNAUTHORIZED',            401, 'warning',  'Authentication required',                     'Missing or invalid credentials'),
    ('INVALID_CREDENTIALS',     400, 'warning',  'Incorrect email or password',                 'Login attempt failed'),
    ('ACCOUNT_INACTIVE',        401, 'warning',  'User account is inactive',                    'Account has been deactivated'),
    ('TOKEN_EXPIRED',           401, 'warning',  'Authentication token has expired',            'Refresh required'),
    ('TOKEN_INVALID',           401, 'warning',  'Authentication token is invalid',             'Token signature or payload is invalid'),
    ('FORBIDDEN',               403, 'warning',  'You do not have permission to perform this',  'Insufficient role/scope'),

    -- Resource lookup
    ('VOLUNTEER_NOT_FOUND',     404, 'warning',  'Volunteer record not found',                  'No volunteer_record row for the given id'),
    ('USER_NOT_FOUND',          404, 'warning',  'User not found',                              'No users row for the given id/email'),
    ('EVENT_NOT_FOUND',         404, 'warning',  'Event not found',                             'No events row for the given id/name'),
    ('ACCESS_LEVEL_NOT_FOUND',  404, 'warning',  'Access level not found',                      'No access_levels row for the given id/name'),
    ('DUTY_TYPE_NOT_FOUND',     404, 'warning',  'Duty type not found',                         'No duty_types row for the given id/name'),
    ('IMPORT_FILE_NOT_FOUND',   404, 'warning',  'Import file not found',                       'No import_file row for the given id'),
    ('NOT_FOUND',               404, 'warning',  'Resource not found',                          'Generic not-found'),

    -- Conflicts / business rules
    ('DUPLICATE_USER',          409, 'warning',  'A user with this email already exists',       'Email collision on register'),
    ('INVALID_STATE_TRANSITION',409, 'warning',  'Invalid state transition',                    'Action not allowed in current state'),
    ('PRINTED_BADGE_LOCKED',    409, 'warning',  'Existing printed badge prevents this action', 'Volunteer already has a printed badge'),

    -- Database / infrastructure
    ('DB_CONNECTION_FAILED',    503, 'critical', 'Database connection failed',                  'Could not connect to the database'),
    ('DB_QUERY_FAILED',         500, 'error',    'Database query failed',                       'A SELECT/UPDATE statement raised an exception'),
    ('DB_INSERT_FAILED',        500, 'error',    'Database insert failed',                      'An INSERT statement raised an exception'),
    ('DB_UPDATE_FAILED',        500, 'error',    'Database update failed',                      'An UPDATE statement raised an exception'),
    ('DB_DELETE_FAILED',        500, 'error',    'Database delete failed',                      'A DELETE statement raised an exception'),
    ('DB_INTEGRITY_ERROR',      409, 'error',    'Database integrity violation',                'Unique / FK / check-constraint violation'),

    -- External services
    ('CENSUS_DB_ERROR',         502, 'error',    'Census database error',                       'Failure querying the census/enrollment database'),
    ('EMAIL_SEND_FAILED',       500, 'warning',  'Failed to send email',                        'SMTP / FastMail error'),

    -- Generic
    ('INTERNAL_ERROR',          500, 'error',    'Internal server error',                       'An unexpected error occurred'),
    ('UNHANDLED_EXCEPTION',     500, 'critical', 'Unhandled exception',                         'No exception handler caught this error')
ON CONFLICT (code) DO UPDATE
    SET status   = EXCLUDED.status,
        severity = EXCLUDED.severity,
        message  = EXCLUDED.message,
        details  = EXCLUDED.details;

-- Quick sanity check
-- SELECT code, status, severity, message FROM error_codes ORDER BY code;
-- SELECT id, request_id, error_code, severity, message, created_at FROM error_logs ORDER BY id DESC LIMIT 20;
