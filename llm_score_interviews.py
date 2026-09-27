"""
Score synthetic interview transcripts using the Google Gemini API
(free tier), against the rubric in docs/scoring_rubric.md.

Requires:
    pip install google-genai
    export GEMINI_API_KEY=your_key_here

Get a free key at https://aistudio.google.com (Get API key -> Create
API key in new project). No billing setup needed for the free tier.

Input:  data/interview_transcripts.csv
Output: data/llm_scores.csv
        (interview_id, competency, llm_score, llm_feedback,
         model, prompt_version, created_at)

Note on reproducibility: PROMPT_VERSION is bumped by hand whenever the
prompt text changes in a way that could affect scores. Old and new
versions are both kept in llm_interview_scores (see the UNIQUE
constraint in llm_schema_and_comparison.sql), so results can be
compared across prompt versions rather than overwritten.
"""

import csv
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

from google import genai

DATA_DIR = "data"
FALLBACK_MODEL = "gemini-3.5-flash-lite"  # used only if auto-discovery fails
PROMPT_VERSION = "prompt_v1"


def pick_available_model(client):
    """Google periodically retires model names (as you've likely just hit).
    Ask the API what's actually available right now instead of hardcoding
    a name that may be gone next month. Prefers a 'flash-lite' model for
    the best free-tier quota, falling back to any flash model, then to
    FALLBACK_MODEL if listing fails entirely."""
    try:
        models = list(client.models.list())
        names = [m.name.replace("models/", "") for m in models
                  if "generateContent" in getattr(m, "supported_actions", [])]
        for name in names:
            if "flash-lite" in name and "preview" not in name:
                print(f"Using model: {name}")
                return name
        for name in names:
            if "flash" in name and "preview" not in name:
                print(f"Using model: {name}")
                return name
    except Exception as e:
        print(f"Could not list models ({e}), falling back to {FALLBACK_MODEL}")
    return FALLBACK_MODEL

RUBRIC = """You are scoring a candidate's interview answers for a Data
Analyst / Recruiter-tools role, using the rubric below. For EACH
dimension, give an integer score from 0-100 and one short sentence of
feedback that cites what in the answer justifies the score.

Scoring principles:
- Score each dimension independently. Strength in one dimension should
  not compensate for weakness in another.
- Score only the evidence contained in the answer. Do not infer
  unstated experience, qualifications, or personality traits.
- If an answer lacks evidence for a high score, score based on the
  evidence actually present rather than assuming the best.

Dimensions (0-40 Low, 41-75 Medium, 76-100 High):
- Communication: clarity, structure, and use of a concrete example suited
  to the audience.
- Technical Depth: soundness of the technical approach, including whether
  trade-offs or edge cases are discussed.
- Problem Solving: whether the answer shows a structured approach —
  diagnosis, fix, and prevention — rather than an ad-hoc one.
- Role Fit: how specifically the candidate's stated motivation and
  background connect to this role's actual work.
- Ownership: whether a concrete example of taking responsibility and
  acting on it (not just acknowledging it) is given.

Respond with ONLY a JSON object, no other text, in this exact shape:
{
  "Communication": {"score": <int>, "feedback": "<one sentence>"},
  "Technical Depth": {"score": <int>, "feedback": "<one sentence>"},
  "Problem Solving": {"score": <int>, "feedback": "<one sentence>"},
  "Role Fit": {"score": <int>, "feedback": "<one sentence>"},
  "Ownership": {"score": <int>, "feedback": "<one sentence>"}
}
"""


def load_transcripts():
    path = os.path.join(DATA_DIR, "interview_transcripts.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_interview = defaultdict(list)
    for r in rows:
        by_interview[r["interview_id"]].append(r)
    return by_interview


def build_prompt(answers):
    parts = [RUBRIC, "\nCandidate's answers:\n"]
    for a in answers:
        parts.append(f"\nQ ({a['competency']}): {a['question']}\nA: {a['answer']}\n")
    return "".join(parts)


def score_interview(client, model, interview_id, answers, retries=2):
    """Call Gemini for one interview, with basic retry + validation."""
    prompt = build_prompt(answers)
    expected_keys = {a["competency"] for a in answers}

    for attempt in range(retries + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
        except Exception as e:
            print(f"  API error on interview {interview_id} (attempt {attempt + 1}): {e}")
            time.sleep(15)
            continue

        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            print(f"  Could not parse JSON for interview {interview_id} (attempt {attempt + 1})")
            continue

        # Validate: all expected competencies present, scores are ints 0-100
        if not expected_keys.issubset(parsed.keys()):
            print(f"  Missing dimensions for interview {interview_id}, got: {list(parsed.keys())}")
            continue
        valid = True
        for comp in expected_keys:
            score = parsed[comp].get("score")
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                print(f"  Invalid score for {comp} on interview {interview_id}: {score}")
                valid = False
        if valid:
            return parsed

    print(f"  Giving up on interview {interview_id} after {retries + 1} attempts.")
    return None


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY as an environment variable first.")

    client = genai.Client(api_key=api_key)
    model = pick_available_model(client)
    by_interview = load_transcripts()

    out_rows = []
    for interview_id, answers in by_interview.items():
        print(f"Scoring interview {interview_id}...")
        parsed = score_interview(client, model, interview_id, answers)
        if parsed is None:
            continue

        now = datetime.now(timezone.utc).isoformat()
        for competency, result in parsed.items():
            out_rows.append({
                "interview_id": interview_id,
                "competency": competency,
                "llm_score": result["score"],
                "llm_feedback": result["feedback"],
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "created_at": now,
            })

        time.sleep(13)  # free tier allows 5 requests/minute -> ~12s minimum gap

    if not out_rows:
        print("No rows scored — nothing written.")
        return

    out_path = os.path.join(DATA_DIR, "llm_scores.csv")
    fieldnames = ["interview_id", "competency", "llm_score", "llm_feedback",
                  "model", "prompt_version", "created_at"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\nWrote {len(out_rows)} scored rows -> {out_path}")


if __name__ == "__main__":
    main()
