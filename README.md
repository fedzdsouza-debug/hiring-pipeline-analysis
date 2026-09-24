# Hiring Pipeline Analysis (PostgreSQL + Python)

A synthetic hiring-funnel dataset and analysis pipeline, modeled on the
job → candidate → interview → decision flow built to demonstrate
relational schema design, SQL analysis (including window functions), and
Python-based synthetic data generation.

## Tech stack

- **PostgreSQL** (hosted on [Supabase](https://supabase.com), free tier)
- **Python** (standard library only — no dependencies to install) for
  synthetic data generation
- **SQL** — joins, aggregations, `FILTER`, and window functions
  (`RANK`, `SUM() OVER`, `LAG`)

## Schema

Six tables, in dependency order:

| Table | Purpose |
|---|---|
| `jobs` | Open roles (title, department, experience level) |
| `candidates` | Applicants, linked to the job they applied for |
| `interviews` | One row per interview conducted (status, timing) |
| `screening_scores` | Pre-interview screening score per candidate |
| `interview_scores` | Per-competency scores within a completed interview |
| `recruiter_decisions` | Final Advance / Reject / Hire decision |

Full DDL is in [`schema.sql`](./schema.sql).

## Key findings

*(from this run's synthetic data — regenerating with a different seed will
produce different numbers)*

- **Funnel:** 150 applied → 121 passed screening → 97 completed interview →
  60 advanced → 2 hired. A realistically narrow funnel, driven by a
  deliberately high bar (avg competency score ≥ 78) for a "Hire" decision.
- **No-shows / interruptions:** ~10% of scheduled interviews each — a
  metric a real recruiting team would want to track and reduce.
- **Most interviews ≠ most hires:** Senior Data Analyst had the most
  completed interviews (16 of 21 applicants) but zero hires, while
  Data Analyst and Recruiter — smaller applicant pools — each produced
  one hire.
- **Weakest competency:** Technical Depth (67.8 avg) and Ownership (68.8)
  scored lowest across all completed interviews; Communication scored
  highest (71.0).
- **Score sanity check:** average competency score by decision was
  Hire 81.9 → Advance 69.6 → Reject 69.1 — a clean separation that
  validates the scoring logic behind the synthetic data.
- **Source effectiveness:** with only 2 hires in this sample, source data
  is too thin to draw reliable conclusions — flagged here rather than
  overstated.

## Files

- `schema.sql` — table definitions, split into runnable steps
- `generate_data.py` — synthetic data generator (no external dependencies)
- `data/` — generated CSVs
- `analysis_queries.sql` — 13 queries across funnel, scores, time-to-stage,
  source effectiveness, and window functions
