"""
Generate synthetic interview transcripts for a sample of completed
interviews, tiered by that interview's average competency score (from
5_interview_scores.csv) so the answer quality roughly tracks the
original synthetic scores WITHOUT literally encoding the number in
the text. This lets an LLM scoring pass be a meaningful comparison
rather than a foregone conclusion.

Output: data/interview_transcripts.csv
Columns: interview_id, candidate_id, job_id, competency, question, answer
"""

import csv
import random
import os

random.seed(7)

DATA_DIR = "data"
SAMPLE_SIZE = 15  # keep small -> keeps LLM API calls cheap

QUESTIONS = {
    "Communication": "Tell me about a time you explained a complex technical concept to a non-technical audience.",
    "Technical Depth": "Walk me through how you would approach analyzing a dataset with a lot of missing values.",
    "Problem Solving": "Describe a challenging problem you solved and how you approached it.",
    "Role Fit": "Why are you interested in this role, and how does your background fit it?",
    "Ownership": "Tell me about a time you took ownership of a mistake or a stalled project.",
}

# Answer banks by tier. Each is a list of paragraph templates; one is
# picked at random and lightly varied per candidate.
ANSWERS = {
    "strong": {
        "Communication": [
            "I once had to explain a churn model to a sales team with no data background. "
            "I skipped the math entirely and used a simple analogy — a leaky bucket — to show "
            "how customers were leaving faster than we were adding new ones. I followed up with "
            "a one-page visual instead of a slide deck full of numbers, and the team was able to "
            "act on it within a week.",

            "A finance director once asked me why a forecast had changed. Instead of walking "
            "through the model, I compared it to a weather forecast updating as new information "
            "comes in — the destination hadn't changed, just our confidence in the exact date. "
            "That framing let us move straight to the decision instead of getting stuck on the math.",

            "I regularly present to people who don't work with data day to day, so I lead with the "
            "decision the number should drive, not the number itself. For a recent report I opened "
            "with 'here's what I'd do based on this' and only pulled up the supporting chart when "
            "someone asked how I got there.",
        ],
        "Technical Depth": [
            "First I'd quantify the missingness — is it random, or does it correlate with another "
            "column? For MCAR data I'd consider simple imputation or dropping rows if the volume "
            "is small; for anything systematic I'd look at model-based imputation or flag it as its "
            "own category, since filling it blindly could bias the results. I'd also document the "
            "decision so anyone downstream knows what was assumed.",

            "I'd start by profiling which columns are missing and whether that's tied to how the "
            "data was collected — a survey question people skip is different from a sensor that "
            "failed. Depending on that, I'd choose between deletion, imputation, or a missing-value "
            "indicator, and I'd always re-run key results with and without the imputed rows to see "
            "how much the conclusion actually depends on that choice.",

            "Missing data isn't one problem, it's several, so I'd separate it by mechanism before "
            "picking a fix. If it's missing completely at random, simple methods are fine. If it's "
            "not, the missingness itself is information, and I'd rather model that explicitly than "
            "paper over it with an average.",
        ],
        "Problem Solving": [
            "A report I owned kept breaking silently because an upstream source changed its schema "
            "without notice. Instead of just patching it, I added schema validation at ingestion so "
            "it would fail loudly and early, then wrote a short runbook so the next person wouldn't "
            "have to debug it from scratch.",

            "Our numbers didn't reconcile with another team's for weeks before anyone noticed. I "
            "traced it back to a timezone mismatch in how two systems logged timestamps, fixed the "
            "join logic, and added an automated daily check comparing totals across both systems so "
            "a future mismatch would surface immediately instead of sitting unnoticed.",

            "When a dashboard's numbers looked implausible, I didn't just re-run it — I worked "
            "backward through each transformation step until I found where a filter was silently "
            "dropping valid rows. Once fixed, I added a row-count sanity check between each stage so "
            "the same class of bug would be caught automatically next time.",
        ],
        "Role Fit": [
            "I've spent years translating messy operational data into decisions non-technical "
            "stakeholders could act on, and this role is the same skill applied to hiring data — "
            "understanding what a funnel is telling you and being able to explain it clearly to "
            "people who aren't analysts themselves.",

            "What draws me to this role specifically is the combination of structured data and a "
            "process people actually care about getting right. I've worked on operational reporting "
            "before, but hiring decisions have real consequences for people, and I want my analysis "
            "work to be in service of something that matters that directly.",

            "I've been on the other side of a messy hiring process, and I know how much a clear, "
            "well-analyzed pipeline changes the experience for both candidates and recruiters. That's "
            "part of why this specific domain interests me, not just the technical work.",
        ],
        "Ownership": [
            "I shipped a dashboard with a formula error that overstated a metric for two weeks. "
            "As soon as I found it, I flagged it to my manager before anyone asked, corrected the "
            "historical numbers, and added an automated check so the same mistake couldn't happen "
            "silently again.",

            "A project I was leading stalled because I'd underestimated how long data cleaning would "
            "take. Rather than let the deadline slip silently, I raised it early with a revised "
            "timeline and a shorter interim deliverable, so the team could still make progress while "
            "the full analysis caught up.",

            "I once sent a report to a client with an outdated figure because I'd pulled from a "
            "cached file instead of the live source. I called it out to my manager myself within the "
            "hour, sent a correction directly to the client, and changed my process so I always "
            "confirm the data source timestamp before sending anything external.",
        ],
    },
    "average": {
        "Communication": [
            "I try to avoid jargon when I'm talking to people outside my team. I usually just "
            "walk them through the main point and use an example if they seem confused.",

            "When I explain something technical, I try to slow down and check if the other person "
            "is following. I don't always have a specific example ready, but I'll try to describe "
            "it in plain terms.",

            "I think I communicate clearly most of the time. If someone doesn't understand, I'll "
            "usually just rephrase what I said in a simpler way.",
        ],
        "Technical Depth": [
            "I'd probably check how many values are missing first. If it's not too many I'd just "
            "fill them in with the average or drop those rows, depending on the situation.",

            "I think it depends on the dataset, but generally I'd look at how much data is missing "
            "and go from there — either remove it or fill it in with something reasonable.",

            "I'd probably ask a more senior analyst what the standard approach is on the team before "
            "deciding, since I know there are a few different ways to handle it.",
        ],
        "Problem Solving": [
            "There was a time a report wasn't matching what finance expected. I went through the "
            "steps again and found a filter that was excluding some records, so I fixed it.",

            "I ran into a situation where two reports disagreed. I compared them line by line until "
            "I found where the numbers diverged and corrected the one that was wrong.",

            "When something breaks I usually start from the beginning and check each step until I "
            "find where it went wrong. It usually takes a bit of trial and error.",
        ],
        "Role Fit": [
            "I've worked with data for a while now and I think this role would let me keep doing "
            "that kind of work, just with a stronger focus on analysis.",

            "This role looks like a good next step for me since it's related to what I've been doing, "
            "and I'd like to grow more into a dedicated analyst position.",

            "I think my background fits reasonably well, and I'm interested in learning more about "
            "this specific industry.",
        ],
        "Ownership": [
            "I made a mistake in a spreadsheet once and it caused some confusion. I let my manager "
            "know and fixed it once I noticed.",

            "There was a report I submitted with an error in it. I corrected it once someone pointed "
            "it out and made sure the update went out to everyone who needed it.",

            "I try to double-check my work, but a mistake still slipped through once. I fixed it "
            "as soon as I realized and moved on.",
        ],
    },
    "weak": {
        "Communication": [
            "I just tell people what I found. If they have questions I answer them.",

            "I don't really change how I explain things depending on who's listening.",

            "I usually just send the report and let people ask if something's unclear.",
        ],
        "Technical Depth": [
            "I'm not totally sure, I think you can just remove the empty rows or use zero instead.",

            "I haven't dealt with that much, I'd probably just Google it.",

            "I'd just leave it as is unless someone told me it was a problem.",
        ],
        "Problem Solving": [
            "I usually ask someone else on the team if something goes wrong and they help me figure "
            "it out.",

            "I'm not sure, I don't think I've had to solve something like that on my own before.",

            "If something breaks I usually just wait to see if it fixes itself or someone else notices.",
        ],
        "Role Fit": [
            "I need a job and this one looked interesting, and I've used Excel before.",

            "I saw the listing and thought I'd apply, I don't know too much about the company yet.",

            "I'm open to a lot of different roles, this one just happened to be available.",
        ],
        "Ownership": [
            "I don't really remember a specific mistake, things mostly go fine when I do them.",

            "I don't think I've made a big mistake at work before.",

            "If something goes wrong it's usually not really up to me to fix it.",
        ],
    },
}


def tier_for(avg_score: float) -> str:
    if avg_score >= 78:
        return "strong"
    elif avg_score >= 60:
        return "average"
    else:
        return "weak"


def load_csv(path):
    with open(os.path.join(DATA_DIR, path), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    interviews = [r for r in load_csv("3_interviews.csv") if r["status"] == "Completed"]
    scores = load_csv("5_interview_scores.csv")

    # average competency score per interview_id
    from collections import defaultdict
    totals = defaultdict(list)
    for s in scores:
        totals[s["interview_id"]].append(float(s["score"]))
    avg_by_interview = {k: sum(v) / len(v) for k, v in totals.items()}

    # Group all completed interviews by tier first. The synthetic data
    # is heavily skewed toward "average" (see generate_data.py's decision
    # rule), so a plain random sample of completed interviews will almost
    # always miss "strong" and "weak" entirely -- which defeats the point
    # of testing whether the LLM can tell good answers from bad ones.
    # Stratified sampling instead: take every strong- and weak-tier
    # interview that exists (there are few), then fill the rest of the
    # sample with a random draw from "average".
    by_tier = defaultdict(list)
    for interview in interviews:
        avg = avg_by_interview.get(interview["interview_id"], 65)
        by_tier[tier_for(avg)].append(interview)

    strong = by_tier["strong"]
    weak = by_tier["weak"]
    n_average = max(0, SAMPLE_SIZE - len(strong) - len(weak))
    average_sample = random.sample(by_tier["average"], min(n_average, len(by_tier["average"])))

    sample = strong + weak + average_sample
    print(f"Stratified sample: {len(strong)} strong, {len(weak)} weak, "
          f"{len(average_sample)} average ({len(sample)} total)")

    rows = []
    for interview in sample:
        iid = interview["interview_id"]
        avg = avg_by_interview.get(iid, 65)
        tier = tier_for(avg)
        for competency, question in QUESTIONS.items():
            answer = random.choice(ANSWERS[tier][competency])
            rows.append({
                "interview_id": iid,
                "candidate_id": interview["candidate_id"],
                "job_id": interview["job_id"],
                "competency": competency,
                "question": question,
                "answer": answer,
                "synthetic_tier": tier,  # kept for our own comparison later, not sent to the LLM
            })

    out_path = os.path.join(DATA_DIR, "interview_transcripts.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} answers across {len(sample)} interviews -> {out_path}")


if __name__ == "__main__":
    main()
