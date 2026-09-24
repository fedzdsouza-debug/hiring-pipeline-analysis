-- ============================================================
-- Analysis Queries: Hiring Pipeline (synthetic data)
-- Run these one at a time in the Supabase SQL Editor.
-- Grouped into: Funnel, Scores, Time-to-stage, Source, Window functions.
-- ============================================================


-- ------------------------------------------------------------
-- SECTION 1: FUNNEL
-- ------------------------------------------------------------

-- Q1. Overall funnel: how many candidates make it through each stage?
SELECT
    (SELECT COUNT(*) FROM candidates)                                   AS applied,
    (SELECT COUNT(*) FROM screening_scores WHERE score >= 50)           AS passed_screening,
    (SELECT COUNT(*) FROM interviews WHERE status = 'Completed')        AS completed_interview,
    (SELECT COUNT(*) FROM recruiter_decisions WHERE decision = 'Advance') AS advanced,
    (SELECT COUNT(*) FROM recruiter_decisions WHERE decision = 'Hire')  AS hired;


-- Q2. Funnel broken down by job, with drop-off at each stage.
SELECT
    j.title,
    COUNT(DISTINCT c.candidate_id)                                        AS applied,
    COUNT(DISTINCT i.candidate_id) FILTER (WHERE i.status = 'Completed')  AS completed_interview,
    COUNT(DISTINCT rd.candidate_id) FILTER (WHERE rd.decision = 'Hire')   AS hired,
    ROUND(
        COUNT(DISTINCT rd.candidate_id) FILTER (WHERE rd.decision = 'Hire')::NUMERIC
        / NULLIF(COUNT(DISTINCT c.candidate_id), 0) * 100, 1
    ) AS hire_rate_pct
FROM jobs j
LEFT JOIN candidates c ON c.job_id = j.job_id
LEFT JOIN interviews i ON i.candidate_id = c.candidate_id
LEFT JOIN recruiter_decisions rd ON rd.candidate_id = c.candidate_id
GROUP BY j.title
ORDER BY applied DESC;


-- Q3. Interview status breakdown (Completed / No-show / Interrupted).
SELECT status, COUNT(*) AS num_interviews,
       ROUND(COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER () * 100, 1) AS pct
FROM interviews
GROUP BY status
ORDER BY num_interviews DESC;


-- ------------------------------------------------------------
-- SECTION 2: SCORES
-- ------------------------------------------------------------

-- Q4. Average screening score by job, highest first.
SELECT j.title, ROUND(AVG(s.score), 1) AS avg_screening_score, COUNT(*) AS n
FROM screening_scores s
JOIN jobs j ON j.job_id = s.job_id
GROUP BY j.title
ORDER BY avg_screening_score DESC;


-- Q5. Average interview score by competency (which skill scores lowest overall?).
SELECT competency, ROUND(AVG(score), 1) AS avg_score, COUNT(*) AS n
FROM interview_scores
GROUP BY competency
ORDER BY avg_score ASC;


-- Q6. Average overall interview score by final decision
-- (sanity check: do Hires actually score higher than Rejects?).
SELECT rd.decision, ROUND(AVG(isc.score), 1) AS avg_competency_score
FROM recruiter_decisions rd
JOIN interviews i ON i.candidate_id = rd.candidate_id AND i.job_id = rd.job_id
JOIN interview_scores isc ON isc.interview_id = i.interview_id
GROUP BY rd.decision
ORDER BY avg_competency_score DESC;


-- ------------------------------------------------------------
-- SECTION 3: TIME-TO-STAGE
-- ------------------------------------------------------------

-- Q7. Average days from application to screening.
SELECT ROUND(AVG(ss.screened_at - c.applied_at), 1) AS avg_days_to_screen
FROM candidates c
JOIN screening_scores ss ON ss.candidate_id = c.candidate_id;


-- Q8. Average days from screening to interview being scheduled.
SELECT ROUND(AVG(i.scheduled_at::DATE - ss.screened_at), 1) AS avg_days_screen_to_interview
FROM screening_scores ss
JOIN interviews i ON i.candidate_id = ss.candidate_id;


-- Q9. Average days from interview completion to final decision
-- ("time to decision" — a metric a real hiring team cares about).
SELECT ROUND(AVG(rd.decided_at - i.completed_at::DATE), 1) AS avg_days_to_decision
FROM interviews i
JOIN recruiter_decisions rd
    ON rd.candidate_id = i.candidate_id AND rd.job_id = i.job_id
WHERE i.status = 'Completed';


-- ------------------------------------------------------------
-- SECTION 4: SOURCE EFFECTIVENESS
-- ------------------------------------------------------------

-- Q10. Which candidate source produces the most hires (conversion rate)?
SELECT
    c.source,
    COUNT(DISTINCT c.candidate_id) AS applied,
    COUNT(DISTINCT rd.candidate_id) FILTER (WHERE rd.decision = 'Hire') AS hired,
    ROUND(
        COUNT(DISTINCT rd.candidate_id) FILTER (WHERE rd.decision = 'Hire')::NUMERIC
        / NULLIF(COUNT(DISTINCT c.candidate_id), 0) * 100, 1
    ) AS hire_rate_pct
FROM candidates c
LEFT JOIN recruiter_decisions rd ON rd.candidate_id = c.candidate_id
GROUP BY c.source
ORDER BY hire_rate_pct DESC;


-- ------------------------------------------------------------
-- SECTION 5: WINDOW FUNCTIONS
-- ------------------------------------------------------------

-- Q11. Rank candidates by screening score within each job
-- (RANK — who's the top candidate for each role?).
SELECT
    j.title,
    c.full_name,
    ss.score,
    RANK() OVER (PARTITION BY j.job_id ORDER BY ss.score DESC) AS rank_in_job
FROM candidates c
JOIN screening_scores ss ON ss.candidate_id = c.candidate_id
JOIN jobs j ON j.job_id = c.job_id
ORDER BY j.title, rank_in_job;


-- Q12. Running total of hires over time
-- (cumulative SUM — good for a "hires over time" trend line).
SELECT
    decided_at,
    COUNT(*) FILTER (WHERE decision = 'Hire') AS hires_that_day,
    SUM(COUNT(*) FILTER (WHERE decision = 'Hire')) OVER (ORDER BY decided_at) AS cumulative_hires
FROM recruiter_decisions
GROUP BY decided_at
ORDER BY decided_at;


-- Q13. Compare each candidate's screening score to the previous candidate
-- who applied for the same job (LAG — spot sudden score drops in the queue).
SELECT
    j.title,
    c.full_name,
    c.applied_at,
    ss.score,
    LAG(ss.score) OVER (PARTITION BY j.job_id ORDER BY c.applied_at) AS prev_candidate_score,
    ss.score - LAG(ss.score) OVER (PARTITION BY j.job_id ORDER BY c.applied_at) AS score_change
FROM candidates c
JOIN screening_scores ss ON ss.candidate_id = c.candidate_id
JOIN jobs j ON j.job_id = c.job_id
ORDER BY j.title, c.applied_at;
