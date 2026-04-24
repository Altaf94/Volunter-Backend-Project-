-- ============================================
-- MINIMAL VOLUNTEER REGISTRATION SCHEMA
-- ============================================

-- Drop tables in dependency order
DROP TABLE IF EXISTS event_access_level_duty_requirements CASCADE;
DROP TABLE IF EXISTS band_type_access_level_duty_type CASCADE;
DROP TABLE IF EXISTS access_level_duty_types CASCADE;
DROP TABLE IF EXISTS band_types CASCADE;
DROP TABLE IF EXISTS duty_types CASCADE;
DROP TABLE IF EXISTS access_levels CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS error_codes CASCADE;

-- 1. Event (9)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Access Level (6)
CREATE TABLE access_levels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Duty Types
CREATE TABLE duty_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Access Level - Duty Types
CREATE TABLE access_level_duty_types (
    id SERIAL PRIMARY KEY,
    access_level_id INTEGER NOT NULL REFERENCES access_levels(id) ON DELETE CASCADE,
    duty_type_id INTEGER NOT NULL REFERENCES duty_types(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (access_level_id, duty_type_id)
);

-- 5. Band Type (6)
CREATE TABLE band_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Band Type - Access Level - Duty Type
CREATE TABLE band_type_access_level_duty_type (
    id SERIAL PRIMARY KEY,
    band_type_id INTEGER NOT NULL REFERENCES band_types(id) ON DELETE CASCADE,
    access_level_id INTEGER NOT NULL REFERENCES access_levels(id) ON DELETE CASCADE,
    duty_type_id INTEGER NOT NULL REFERENCES duty_types(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (band_type_id, access_level_id, duty_type_id)
);

-- 7. Event - Access Level - Duty - RequiredCount, Remaining
CREATE TABLE event_access_level_duty_requirements (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    access_level_id INTEGER NOT NULL REFERENCES access_levels(id) ON DELETE CASCADE,
    duty_type_id INTEGER NOT NULL REFERENCES duty_types(id) ON DELETE CASCADE,
    required_count INTEGER NOT NULL DEFAULT 0 CHECK (required_count >= 0),
    remaining INTEGER NOT NULL DEFAULT 0 CHECK (remaining >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (event_id, access_level_id, duty_type_id)
);

CREATE INDEX idx_access_level_duty_types_access_level_id
    ON access_level_duty_types (access_level_id);

CREATE INDEX idx_access_level_duty_types_duty_type_id
    ON access_level_duty_types (duty_type_id);

CREATE INDEX idx_band_type_access_level_duty_type_band_type_id
    ON band_type_access_level_duty_type (band_type_id);

CREATE INDEX idx_band_type_access_level_duty_type_access_level_id
    ON band_type_access_level_duty_type (access_level_id);

CREATE INDEX idx_band_type_access_level_duty_type_duty_type_id
    ON band_type_access_level_duty_type (duty_type_id);

CREATE INDEX idx_event_access_level_duty_requirements_event_id
    ON event_access_level_duty_requirements (event_id);

CREATE INDEX idx_event_access_level_duty_requirements_access_level_id
    ON event_access_level_duty_requirements (access_level_id);

CREATE INDEX idx_event_access_level_duty_requirements_duty_type_id
    ON event_access_level_duty_requirements (duty_type_id);

-- ============================================
-- Error Codes
-- ============================================
CREATE TABLE error_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    http_status INTEGER,
    severity VARCHAR(20) NOT NULL DEFAULT 'error', -- e.g. info, warning, error
    message VARCHAR(255) NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Users (login + profile)
-- ============================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL,
    scope VARCHAR(20) CHECK (scope IN ('national','regional')),
    region_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role_id ON users (role_id);
CREATE INDEX idx_users_region_id ON users (region_id);



-- ============================================
-- Roles
-- ============================================
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    scope VARCHAR(20) NOT NULL CHECK (scope IN ('national','regional')),
    name VARCHAR(100) NOT NULL,
    can_view BOOLEAN NOT NULL DEFAULT FALSE,
    can_make BOOLEAN NOT NULL DEFAULT FALSE,
    can_check BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (scope, name)
);


    -- ============================================
    -- Import File Log
    -- ============================================
    CREATE TABLE import_file (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        import_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        file_name VARCHAR(255) NOT NULL,
        record_count INTEGER NOT NULL DEFAULT 0,
        status VARCHAR(50) NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_import_file_user_id ON import_file (user_id);


    -- ============================================
    -- Volunteer Records
    -- ============================================
    CREATE TABLE volunteer_record (
        id SERIAL PRIMARY KEY,
        record_number INTEGER NOT NULL,
        cnic VARCHAR(30),
        name VARCHAR(200),
        event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
        access_level_id INTEGER REFERENCES access_levels(id) ON DELETE SET NULL,
        duty_type_id INTEGER REFERENCES duty_types(id) ON DELETE SET NULL,
        record_status VARCHAR(20) NOT NULL CHECK (record_status IN ('maker','checker','printed')),
        decision_status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (decision_status IN ('Rejected','Ok','Discrepant-1','Discrepant-2','pending')),
        register VARCHAR(3) NOT NULL DEFAULT 'No' CHECK (register IN ('Yes','No')),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        checker_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        import_id INTEGER REFERENCES import_file(id) ON DELETE SET NULL
    );

    CREATE INDEX idx_volunteer_record_cnic ON volunteer_record (cnic);
    CREATE INDEX idx_volunteer_record_event_id ON volunteer_record (event_id);



