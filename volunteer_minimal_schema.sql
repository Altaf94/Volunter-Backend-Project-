-- ============================================
-- VOLUNTEER MANAGEMENT - MINIMAL DATABASE SCHEMA
-- Pakistan Deedar 2026
-- Only stores what frontend can't handle locally
-- ============================================

-- Use main database or create separate
-- CREATE DATABASE volunteer_db;

-- ============================================
-- CORE TABLE: VOLUNTEERS
-- Stores volunteer records from Excel uploads
-- ============================================

CREATE TABLE IF NOT EXISTS volunteers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    volunteer_id VARCHAR(20) UNIQUE NOT NULL,  -- VID-XXXXXX
    cnic VARCHAR(15) NOT NULL,                 -- 12345-1234567-1
    name VARCHAR(200) NOT NULL,
    
    -- Event & Duty (from Excel)
    event_number INT NOT NULL CHECK (event_number BETWEEN 1 AND 9),
    access_level INT NOT NULL CHECK (access_level BETWEEN 1 AND 5),
    duty_type VARCHAR(50) NOT NULL,
    
    -- Source Info (selected on upload)
    region VARCHAR(20) NOT NULL,               -- gilgit, hunza, etc.
    source VARCHAR(30) NOT NULL,               -- local_council, itreb, health_board
    source_entity_id VARCHAR(50),
    source_entity_name VARCHAR(200),
    
    -- Upload Batch Reference
    batch_id VARCHAR(50) NOT NULL,
    row_number INT,
    
    -- Workflow Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- Status values: pending, valid, rejected, discrepant, submitted, approved, printed, dispatched
    
    -- CNIC Verification (from batch check)
    cnic_verified BOOLEAN DEFAULT FALSE,
    cnic_registered_name VARCHAR(200),         -- Name from enrollment DB
    
    -- Validation Info (from frontend)
    validation_errors JSONB DEFAULT '[]'::jsonb,
    
    -- Workflow Tracking
    submitted_at TIMESTAMP,
    submitted_by VARCHAR(100),
    approved_at TIMESTAMP,
    approved_by VARCHAR(100),
    rejected_at TIMESTAMP,
    rejected_by VARCHAR(100),
    rejection_reason TEXT,
    
    -- Print & Dispatch
    print_batch_id VARCHAR(50),
    printed_at TIMESTAMP,
    printed_by VARCHAR(100),
    dispatch_package_id VARCHAR(50),
    dispatched_at TIMESTAMP,
    dispatched_by VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- UPLOAD BATCHES
-- Track each Excel upload
-- ============================================

CREATE TABLE IF NOT EXISTS upload_batches (
    id VARCHAR(50) PRIMARY KEY,                -- batch-YYYYMMDDHHMMSS-XXXX
    file_name VARCHAR(255) NOT NULL,
    region VARCHAR(20) NOT NULL,
    source VARCHAR(30) NOT NULL,
    source_entity_id VARCHAR(50),
    source_entity_name VARCHAR(200),
    
    -- Counts
    total_records INT DEFAULT 0,
    valid_records INT DEFAULT 0,
    rejected_records INT DEFAULT 0,
    discrepant_records INT DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'processing',   -- processing, completed, failed
    
    -- User Info
    uploaded_by VARCHAR(100),
    uploaded_by_name VARCHAR(200),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- ============================================
-- PRINT BATCHES
-- Group volunteers for printing
-- ============================================

CREATE TABLE IF NOT EXISTS print_batches (
    id VARCHAR(50) PRIMARY KEY,                -- print-YYYYMMDDHHMMSS-XXXX
    region VARCHAR(20) NOT NULL,
    
    -- Counts
    total_badges INT DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',      -- pending, printing, completed, failed
    
    -- User Info
    created_by VARCHAR(100),
    created_by_name VARCHAR(200),
    printed_by VARCHAR(100),
    printed_by_name VARCHAR(200),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    printed_at TIMESTAMP
);

-- ============================================
-- DISPATCH PACKAGES
-- Group print batches for dispatch
-- ============================================

CREATE TABLE IF NOT EXISTS dispatch_packages (
    id VARCHAR(50) PRIMARY KEY,                -- dispatch-YYYYMMDDHHMMSS-XXXX
    region VARCHAR(20) NOT NULL,
    
    -- Destination
    destination VARCHAR(30) NOT NULL,          -- local_council, itreb, health_board
    destination_entity_id VARCHAR(50),
    destination_entity_name VARCHAR(200),
    
    -- Counts
    total_badges INT DEFAULT 0,
    total_print_batches INT DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'preparing',    -- preparing, ready, dispatched, received
    
    -- User Info
    prepared_by VARCHAR(100),
    dispatched_by VARCHAR(100),
    received_by VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dispatched_at TIMESTAMP,
    received_at TIMESTAMP
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_volunteers_cnic ON volunteers(cnic);
CREATE INDEX IF NOT EXISTS idx_volunteers_batch ON volunteers(batch_id);
CREATE INDEX IF NOT EXISTS idx_volunteers_region ON volunteers(region);
CREATE INDEX IF NOT EXISTS idx_volunteers_status ON volunteers(status);
CREATE INDEX IF NOT EXISTS idx_volunteers_event ON volunteers(event_number);
CREATE INDEX IF NOT EXISTS idx_volunteers_cnic_event ON volunteers(cnic, event_number);
CREATE INDEX IF NOT EXISTS idx_volunteers_region_status ON volunteers(region, status);

CREATE INDEX IF NOT EXISTS idx_batches_region ON upload_batches(region);
CREATE INDEX IF NOT EXISTS idx_batches_status ON upload_batches(status);

-- ============================================
-- HELPER FUNCTION: Generate Volunteer ID
-- ============================================

CREATE OR REPLACE FUNCTION generate_volunteer_id()
RETURNS VARCHAR(20) AS $$
BEGIN
    RETURN 'VID-' || UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 6));
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGER: Auto-update updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER volunteers_updated_at
    BEFORE UPDATE ON volunteers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
