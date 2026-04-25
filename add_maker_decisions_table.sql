-- ============================================
-- MAKER DECISIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS maker_decisions (
    id SERIAL PRIMARY KEY,
    volunteer_record_id INTEGER NOT NULL REFERENCES volunteer_record(id) ON DELETE CASCADE,
    maker_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    decision_status VARCHAR(50) NOT NULL CHECK (decision_status IN ('Ok', 'Rejected', 'Discrepant-1', 'Discrepant-2')),
    reason TEXT,
    -- Store full record details for checker review
    record_number INTEGER,
    cnic VARCHAR(30),
    name VARCHAR(200),
    event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
    access_level_id INTEGER REFERENCES access_levels(id) ON DELETE SET NULL,
    duty_type_id INTEGER REFERENCES duty_types(id) ON DELETE SET NULL,
    record_status VARCHAR(20),
    register VARCHAR(3),
    checker_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    import_id INTEGER REFERENCES import_file(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_maker_decisions_volunteer_record_id ON maker_decisions (volunteer_record_id);
CREATE INDEX idx_maker_decisions_maker_id ON maker_decisions (maker_id);
CREATE INDEX idx_maker_decisions_created_at ON maker_decisions (created_at);