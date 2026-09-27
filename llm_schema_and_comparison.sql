-- ============================================================
-- LLM Scoring: table + comparison against the reference (synthetic)
-- interview_scores. Run in the SQL Editor after generating and
-- importing data/llm_scores.csv.
--
-- Naming note: interview_scores is referred to as the "reference"
-- score below, not "ground truth" — it was itself synthetically
-- generated, not independently verified. See docs/scoring_rubric.md.
-- ============================================================

-- ---------- STEP 1: create the table ----------
CREATE TABLE llm_interview_scores (
    llm_score_id      SERIAL PRIMARY KEY,
    interview_id      INTEGER NOT NULL REFERENCES interviews(interview_id),
    competency        VARCHAR(50) NOT NULL,
    llm_score         NUMERIC(5,2) NOT NULL,
    llm_feedback      TEXT,
    model             VARCHAR(50) NOT NULL,   -- e.g. 'gemini-2.5-flash'
    prompt_version    VARCHAR(20) NOT NULL,   -- e.g. 'prompt_v1'
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (interview_id, competency, prompt_version)
);

-- ---------- STEP 2: import data/llm_scores.csv ----------
-- Table Editor -> llm_interview_scores -> Insert -> Import data from CSV

-- ---------- STEP 3: row-by-row comparison ----------
SELECT
    isc.interview_id,
    isc.competency,
    isc.score        AS reference_score,
    llm.llm_score,
    ROUND(llm.llm_score - isc.score, 1) AS score_diff,
    llm.model,
    llm.prompt_version,
    llm.llm_feedback
FROM interview_scores isc
JOIN llm_interview_scores llm
    ON llm.interview_id = isc.interview_id
    AND llm.competency = isc.competency
ORDER BY isc.interview_id, isc.competency;

-- ---------- STEP 4: agreement metrics per competency ----------
-- Mean Absolute Error and average signed difference (systematic bias),
-- per dimension.
SELECT
    isc.competency,
    ROUND(AVG(isc.score), 1)                      AS avg_reference_score,
    ROUND(AVG(llm.llm_score), 1)                  AS avg_llm_score,
    ROUND(AVG(llm.llm_score - isc.score), 1)      AS avg_signed_diff,
    ROUND(AVG(ABS(llm.llm_score - isc.score)), 1) AS mean_absolute_error,
    COUNT(*) FILTER (WHERE ABS(llm.llm_score - isc.score) <= 10) AS within_10pts,
    COUNT(*)                                       AS n
FROM interview_scores isc
JOIN llm_interview_scores llm
    ON llm.interview_id = isc.interview_id
    AND llm.competency = isc.competency
GROUP BY isc.competency
ORDER BY mean_absolute_error DESC;

-- ---------- STEP 5: overall MAE across all dimensions ----------
SELECT
    ROUND(AVG(ABS(llm.llm_score - isc.score)), 1) AS overall_mae,
    COUNT(*) AS n_scored_pairs
FROM interview_scores isc
JOIN llm_interview_scores llm
    ON llm.interview_id = isc.interview_id
    AND llm.competency = isc.competency;
