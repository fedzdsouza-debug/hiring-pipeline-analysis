"""
Generate synthetic hiring-pipeline data matching schema.sql.

No external dependencies beyond the Python standard library, so it
runs anywhere without pip installs. Produces one CSV per table in
./data, in an order that respects foreign-key dependencies:

    jobs -> candidates -> interviews -> screening_scores
         -> interview_scores -> recruiter_decisions

Each CSV's first column matches the table's SERIAL primary key
(starting at 1), so you can import them straight into Supabase via
Table Editor > Insert > Import data from CSV, in this same order.
"""

import csv
import random
from datetime import date, datetime, timedelta

random.seed(42)  # reproducible output

OUT_DIR = "data"
import os
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Reference data
# ------------------------------------------------------------------

JOB_TITLES = [
    ("Data Analyst", "Analytics", "Entry"),
    ("Senior Data Analyst", "Analytics", "Senior"),
    ("Backend Engineer", "Engineering", "Mid"),
    ("Product Manager", "Product", "Mid"),
    ("Recruiter", "People", "Entry"),
    ("Customer Success Associate", "Customer Success", "Entry"),
    ("QA Engineer", "Engineering", "Mid"),
    ("Operations Analyst", "Operations", "Entry"),
]
INTERVIEW_MODES = ["Standard", "Individualized"]
SOURCES = ["LinkedIn", "Referral", "Job Board", "Company Website", "Campus"]
FIRST_NAMES = ["Aarav","Priya","Rohan","Sneha","Karan","Meera","Arjun","Divya",
               "Vikram","Anjali","Ravi","Pooja","Amit","Neha","Sanjay","Isha",
               "Rahul","Kavya","Nikhil","Shreya","Dev","Tara","Yash","Simran",
               "Aditya","Riya","Manav","Ananya","Varun","Sana"]
LAST_NAMES = ["Sharma","Verma","Menon","Nair","Reddy","Gupta","Iyer","Patel",
              "Shah","Kulkarni","Joshi","Rao","D'Souza","Fernandes","Pillai",
              "Chawla","Malhotra","Agarwal","Bose","Kapoor"]
COMPETENCIES = ["Communication", "Technical Depth", "Problem Solving",
                 "Role Fit", "Ownership"]
DECISIONS = ["Advance", "Reject", "Hire"]
RECRUITERS = ["A. Fernandes", "S. Kulkarni", "R. Menon", "P. Shah"]

N_CANDIDATES = 150

def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def rand_datetime(base_date: date, hour_start=9, hour_end=17) -> datetime:
    hour = random.randint(hour_start, hour_end)
    minute = random.choice([0, 15, 30, 45])
    return datetime(base_date.year, base_date.month, base_date.day, hour, minute)

# ------------------------------------------------------------------
# 1. jobs
# ------------------------------------------------------------------
jobs = []
for i, (title, dept, level) in enumerate(JOB_TITLES, start=1):
    jobs.append({
        "job_id": i,
        "title": title,
        "department": dept,
        "experience_level": level,
        "interview_mode": random.choice(INTERVIEW_MODES),
        "created_at": rand_date(date(2026, 1, 1), date(2026, 3, 1)).isoformat(),
    })

# ------------------------------------------------------------------
# 2. candidates
# ------------------------------------------------------------------
candidates = []
for cid in range(1, N_CANDIDATES + 1):
    job = random.choice(jobs)
    applied = rand_date(date(2026, 3, 1), date(2026, 8, 1))
    candidates.append({
        "candidate_id": cid,
        "full_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "job_id": job["job_id"],
        "source": random.choice(SOURCES),
        "applied_at": applied.isoformat(),
    })

# ------------------------------------------------------------------
# 3. screening_scores  (every candidate gets screened)
# ------------------------------------------------------------------
screening_scores = []
for i, cand in enumerate(candidates, start=1):
    screening_scores.append({
        "screening_id": i,
        "candidate_id": cand["candidate_id"],
        "job_id": cand["job_id"],
        "score": round(random.gauss(65, 15), 2) if True else 0,
        "screened_at": (date.fromisoformat(cand["applied_at"]) +
                         timedelta(days=random.randint(1, 5))).isoformat(),
    })
    screening_scores[-1]["score"] = max(0, min(100, screening_scores[-1]["score"]))

# ------------------------------------------------------------------
# 4. interviews  (candidates who screened >= 50 move to interview)
# ------------------------------------------------------------------
interviews = []
interview_id = 1
for cand, screen in zip(candidates, screening_scores):
    if screen["score"] < 50:
        continue  # didn't pass screening, no interview
    scheduled = date.fromisoformat(screen["screened_at"]) + timedelta(days=random.randint(2, 10))
    status = random.choices(
        ["Completed", "No-show", "Interrupted"], weights=[0.8, 0.1, 0.1]
    )[0]
    scheduled_dt = rand_datetime(scheduled)
    completed_dt = None
    duration = None
    if status == "Completed":
        duration = random.randint(20, 55)
        completed_dt = scheduled_dt + timedelta(minutes=duration)
    elif status == "Interrupted":
        duration = random.randint(5, 15)
        completed_dt = scheduled_dt + timedelta(minutes=duration)

    interviews.append({
        "interview_id": interview_id,
        "candidate_id": cand["candidate_id"],
        "job_id": cand["job_id"],
        "status": status,
        "scheduled_at": scheduled_dt.isoformat(sep=" "),
        "completed_at": completed_dt.isoformat(sep=" ") if completed_dt else "",
        "duration_minutes": duration if duration else "",
    })
    interview_id += 1

# ------------------------------------------------------------------
# 5. interview_scores  (only for Completed interviews, one row per competency)
# ------------------------------------------------------------------
interview_scores = []
score_id = 1
for interview in interviews:
    if interview["status"] != "Completed":
        continue
    for comp in COMPETENCIES:
        interview_scores.append({
            "score_id": score_id,
            "interview_id": interview["interview_id"],
            "competency": comp,
            "score": max(0, min(100, round(random.gauss(70, 12), 2))),
        })
        score_id += 1

# ------------------------------------------------------------------
# 6. recruiter_decisions  (only for Completed interviews)
# ------------------------------------------------------------------
recruiter_decisions = []
decision_id = 1
for interview in interviews:
    if interview["status"] != "Completed":
        continue
    # Average this interview's competency scores to bias the decision
    scores = [s["score"] for s in interview_scores if s["interview_id"] == interview["interview_id"]]
    avg = sum(scores) / len(scores) if scores else 50
    if avg >= 78:
        decision = "Hire"
    elif avg >= 60:
        decision = random.choices(["Advance", "Reject"], weights=[0.6, 0.4])[0]
    else:
        decision = "Reject"

    decided = (datetime.fromisoformat(interview["completed_at"]).date()
               + timedelta(days=random.randint(1, 4)))
    recruiter_decisions.append({
        "decision_id": decision_id,
        "candidate_id": interview["candidate_id"],
        "job_id": interview["job_id"],
        "decision": decision,
        "recruiter_name": random.choice(RECRUITERS),
        "decided_at": decided.isoformat(),
    })
    decision_id += 1

# ------------------------------------------------------------------
# Write CSVs
# ------------------------------------------------------------------
def write_csv(filename, rows):
    if not rows:
        return
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {path}")

write_csv("1_jobs.csv", jobs)
write_csv("2_candidates.csv", candidates)
write_csv("3_interviews.csv", interviews)
write_csv("4_screening_scores.csv", screening_scores)
write_csv("5_interview_scores.csv", interview_scores)
write_csv("6_recruiter_decisions.csv", recruiter_decisions)

print("\nDone. Import the CSVs into Supabase in this numeric order")
print("(Table Editor > select table > Insert > Import data from CSV).")
