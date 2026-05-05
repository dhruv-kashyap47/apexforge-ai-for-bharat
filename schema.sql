-- ApexForge AI Database Schema
-- Unified Business Identity System

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS review_queue CASCADE;
DROP TABLE IF EXISTS match_logs CASCADE;
DROP TABLE IF EXISTS raw_records CASCADE;
DROP TABLE IF EXISTS matched_groups CASCADE;
DROP TABLE IF EXISTS ubid_registry CASCADE;

-- ============================================
-- Table 1: raw_records
-- Stores all uploaded business records
-- ============================================
CREATE TABLE raw_records (
    id SERIAL PRIMARY KEY,
    upload_batch_id VARCHAR(50) NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    pan VARCHAR(20),
    gstin VARCHAR(20),
    address TEXT,
    pincode VARCHAR(10),
    district VARCHAR(100),
    state VARCHAR(100),
    registration_date DATE,
    last_activity_date DATE,
    department VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cleaned_name VARCHAR(255),
    cleaned_pan VARCHAR(20),
    cleaned_gstin VARCHAR(20),
    cleaned_address TEXT,
    normalized_pincode VARCHAR(10),
    name_phonetic VARCHAR(255)
);

CREATE INDEX idx_raw_records_batch ON raw_records(upload_batch_id);
CREATE INDEX idx_raw_records_pan ON raw_records(pan);
CREATE INDEX idx_raw_records_gstin ON raw_records(gstin);
CREATE INDEX idx_raw_records_pincode ON raw_records(pincode);
CREATE INDEX idx_raw_records_district ON raw_records(district);
CREATE INDEX idx_raw_records_state ON raw_records(state);

-- ============================================
-- Table 2: matched_groups
-- Links raw records to their UBID groups
-- ============================================
CREATE TABLE matched_groups (
    id SERIAL PRIMARY KEY,
    ubid VARCHAR(20) NOT NULL UNIQUE,
    master_record_id INTEGER REFERENCES raw_records(id),
    record_ids INTEGER[] NOT NULL,
    match_confidence DECIMAL(5,2) NOT NULL,
    match_tier VARCHAR(20) NOT NULL CHECK (match_tier IN ('Tier1', 'Tier2', 'Tier3')),
    match_reason TEXT,
    matched_fields TEXT[],
    status VARCHAR(20) DEFAULT 'Active' CHECK (status IN ('Active', 'Merged', 'Split', 'UnderReview')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_matched_groups_ubid ON matched_groups(ubid);
CREATE INDEX idx_matched_groups_confidence ON matched_groups(match_confidence);
CREATE INDEX idx_matched_groups_tier ON matched_groups(match_tier);

-- ============================================
-- Table 3: ubid_registry
-- Central registry of all UBIDs with business status
-- ============================================
CREATE TABLE ubid_registry (
    id SERIAL PRIMARY KEY,
    ubid VARCHAR(20) NOT NULL UNIQUE,
    state_code VARCHAR(2) NOT NULL,
    district_code VARCHAR(3) NOT NULL,
    category VARCHAR(10) NOT NULL,
    sequence_number INTEGER NOT NULL,
    business_name VARCHAR(255),
    primary_pan VARCHAR(20),
    primary_gstin VARCHAR(20),
    business_status VARCHAR(20) NOT NULL CHECK (business_status IN ('Active', 'Dormant', 'Closed')),
    status_reason TEXT,
    total_records INTEGER DEFAULT 1,
    last_activity_date DATE,
    registration_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ubid_registry_ubid ON ubid_registry(ubid);
CREATE INDEX idx_ubid_registry_status ON ubid_registry(business_status);
CREATE INDEX idx_ubid_registry_state ON ubid_registry(state_code);

-- ============================================
-- Table 4: match_logs
-- Audit trail of all matching operations
-- ============================================
CREATE TABLE match_logs (
    id SERIAL PRIMARY KEY,
    upload_batch_id VARCHAR(50) NOT NULL,
    record1_id INTEGER REFERENCES raw_records(id),
    record2_id INTEGER REFERENCES raw_records(id),
    match_score DECIMAL(5,2) NOT NULL,
    match_tier VARCHAR(20) NOT NULL,
    match_fields JSONB,
    match_decision VARCHAR(20) NOT NULL CHECK (match_decision IN ('AutoMerge', 'NeedsReview', 'KeepSeparate', 'Approved', 'Rejected')),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_by VARCHAR(100) DEFAULT 'system'
);

CREATE INDEX idx_match_logs_batch ON match_logs(upload_batch_id);
CREATE INDEX idx_match_logs_decision ON match_logs(match_decision);

-- ============================================
-- Table 5: review_queue
-- Queue for matches requiring manual review
-- ============================================
CREATE TABLE review_queue (
    id SERIAL PRIMARY KEY,
    match_group_id INTEGER REFERENCES matched_groups(id),
    record1_id INTEGER REFERENCES raw_records(id),
    record2_id INTEGER REFERENCES raw_records(id),
    match_score DECIMAL(5,2) NOT NULL,
    match_details JSONB,
    status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Escalated')),
    reviewer_notes TEXT,
    assigned_to VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(100)
);

CREATE INDEX idx_review_queue_status ON review_queue(status);
CREATE INDEX idx_review_queue_score ON review_queue(match_score);

-- ============================================
-- Functions
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_matched_groups_updated_at BEFORE UPDATE ON matched_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ubid_registry_updated_at BEFORE UPDATE ON ubid_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Views for common queries
-- ============================================

-- View: Active businesses summary
CREATE VIEW vw_active_businesses AS
SELECT 
    u.ubid,
    u.business_name,
    u.business_status,
    u.state_code,
    u.district_code,
    u.total_records,
    u.last_activity_date,
    mg.match_confidence,
    mg.match_tier
FROM ubid_registry u
LEFT JOIN matched_groups mg ON u.ubid = mg.ubid
WHERE u.business_status = 'Active';

-- View: Pending review summary
CREATE VIEW vw_pending_reviews AS
SELECT 
    rq.id as review_id,
    rq.match_score,
    rq.match_details,
    rq.status,
    rq.created_at,
    r1.business_name as record1_name,
    r1.pan as record1_pan,
    r1.gstin as record1_gstin,
    r2.business_name as record2_name,
    r2.pan as record2_pan,
    r2.gstin as record2_gstin
FROM review_queue rq
JOIN raw_records r1 ON rq.record1_id = r1.id
JOIN raw_records r2 ON rq.record2_id = r2.id
WHERE rq.status = 'Pending';
