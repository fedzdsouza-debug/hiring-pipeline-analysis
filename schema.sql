-- ---------- STEP 1: jobs ----------
-- One row per open role.
CREATE TABLE jobs (
    job_id            SERIAL PRIMARY KEY,
    title             VARCHAR(100) NOT NULL,
    department        VARCHAR(50),
    experience_level  VARCHAR(30),   -- e.g. 'Entry', 'Mid', 'Senior'
    interview_mode    VARCHAR(20),   -- 'Standard' or 'Individualized'
    created_at        DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ---------- STEP 2: candidates ----------
-- One row per applicant. Linked to the job they applied for.
CREATE TABLE candidates (
    candidate_id      SERIAL PRIMARY KEY,
    full_name         VARCHAR(100) NOT NULL,
    job_id            INTEGER NOT NULL REFERENCES jobs(job_id),
    source            VARCHAR(50),   -- e.g. 'LinkedIn', 'Referral', 'Job Board'
    applied_at        DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ---------- STEP 3: interviews ----------
-- One row per interview conducted for a candidate.
CREATE TABLE interviews (
    interview_id      SERIAL PRIMARY KEY,
    candidate_id      INTEGER NOT NULL REFERENCES candidates(candidate_id),
    job_id            INTEGER NOT NULL REFERENCES jobs(job_id),
    status            VARCHAR(20) NOT NULL, -- 'Scheduled','Completed','No-show','Interrupted'
    scheduled_at      TIMESTAMP,
    completed_at      TIMESTAMP,
    duration_minutes  INTEGER
);

-- ---------- STEP 4: screening_scores ----------
-- Pre-interview background screening score against the job requirements.
CREATE TABLE screening_scores (
    screening_id      SERIAL PRIMARY KEY,
    candidate_id      INTEGER NOT NULL REFERENCES candidates(candidate_id),
    job_id            INTEGER NOT NULL REFERENCES jobs(job_id),
    score             NUMERIC(5,2) NOT NULL, -- 0-100
    screened_at       DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ---------- STEP 5: interview_scores ----------
-- Per-competency scores within a completed interview (one interview can
-- have several rows, one per competency evaluated). 
CREATE TABLE interview_scores (
    score_id          SERIAL PRIMARY KEY,
    interview_id      INTEGER NOT NULL REFERENCES interviews(interview_id),
    competency        VARCHAR(50) NOT NULL, -- e.g. 'Communication','Technical Depth'
    score             NUMERIC(5,2) NOT NULL,
    UNIQUE (interview_id, competency)
);

-- ---------- STEP 6: recruiter_decisions ----------
-- Final decision made by the hiring team for each candidate.
CREATE TABLE recruiter_decisions (
    decision_id       SERIAL PRIMARY KEY,
    candidate_id      INTEGER NOT NULL REFERENCES candidates(candidate_id),
    job_id            INTEGER NOT NULL REFERENCES jobs(job_id),
    decision          VARCHAR(20) NOT NULL, -- 'Advance','Reject','Hire'
    recruiter_name    VARCHAR(100),
    decided_at        DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ---------- STEP 7 (optional check): confirm all tables exist ----------
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' ORDER BY table_name;
