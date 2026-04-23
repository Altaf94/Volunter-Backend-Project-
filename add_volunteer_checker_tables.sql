-- add_volunteer_checker_tables.sql
CREATE TABLE volunteers (
    id SERIAL PRIMARY KEY,
    cnic VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    event_name VARCHAR(100),
    access_level VARCHAR(50),
    duty_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'Awaiting Checker',
    discrepancy_type INT DEFAULT 0,
    discrepancy_reason TEXT
);
