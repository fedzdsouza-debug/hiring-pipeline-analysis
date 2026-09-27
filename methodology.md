# LLM Scoring Experiment: Methodology & Findings

## What this experiment tests

Whether an LLM (Google Gemini, free tier) can apply the rubric in
`scoring_rubric.md` to candidate interview answers, and how its scores
compare to this project's synthetic reference scores.

**This is not a validation of Gemini as a hiring tool.** It's an
experiment in LLM-based evaluation against a defined rubric, using
synthetic data. See "Limitations" below for what this can and can't tell us.

## Setup

- **Model:** auto-discovered at runtime via the Gemini API (the free-tier
  `flash-lite` models were retired twice during this project — see
  `llm_score_interviews.py` for why the model name isn't hardcoded).
- **Prompt version:** `prompt_v1` (see `scoring_rubric.md`).
- **Sample:** 15 completed interviews, **stratified by reference tier**
  (2 strong, 3 weak, 10 average — this is every strong/weak interview
  that exists in the 97-interview synthetic dataset, plus a random draw
  of average ones). An initial random sample of 15 happened to be 100%
  "average" tier by chance, which produced a degenerate result (zero
  score variance on one dimension) — switching to stratified sampling
  was a direct fix for that.
- **Answer diversity:** each tier/competency combination has 2-3 distinct
  hand-written answer templates, to avoid sending the literal same text
  to the model repeatedly within a tier.

## Results

### Absolute score agreement

Overall MAE (Mean Absolute Error) across all 75 scored pairs: **33.3**
(on a 0-100 scale). Every dimension shows the LLM scoring **19-40
points lower** than the reference score, and only 1-3 of 15 pairs per
dimension land within 10 points of the reference:

| Dimension | Avg reference | Avg LLM | MAE | Within 10pts |
|---|---|---|---|---|
| Technical Depth | 71.2 | 31.3 | 40.8 | 1/15 |
| Communication | 66.5 | 30.7 | 39.4 | 1/15 |
| Role Fit | 73.4 | 38.9 | 35.7 | 2/15 |
| Problem Solving | 66.4 | 45.0 | 25.5 | 3/15 |
| Ownership | 64.1 | 44.7 | 25.2 | 1/15 |

**This large gap is expected, not a failure of either method.** The
reference `interview_scores` were generated as independent random draws
(`gauss(70, 12)`) per dimension, not derived from the answer text —
only the *tier* used to pick which answer template to write came from
that interview's average score. The LLM, by contrast, is scoring the
actual text. Two different processes measuring different things will
disagree on absolute scale.

### Rank agreement

A more meaningful question given the above: does the LLM still *rank*
candidates similarly to the reference, even on a different scale?
Measured via Pearson correlation on ranks (a Spearman approximation,
since Postgres has no native Spearman function):

| Dimension | Rank correlation |
|---|---|
| Problem Solving | 0.65 |
| Technical Depth | 0.65 |
| Role Fit | 0.64 |
| Ownership | 0.55 |
| Communication | 0.01 |

Four of five dimensions show a moderate positive rank correlation —
despite disagreeing sharply on absolute scale, the LLM broadly agrees
with the reference on relative ordering for Problem Solving, Technical
Depth, Role Fit, and Ownership. That's a more useful signal than raw
MAE: a consistently-recalibrated-but-well-ordered scorer could still be
useful for relative comparison (ranking candidates against each other),
even if unsuitable for an absolute cutoff.

**Communication is the exception**, at a rank correlation of 0.01 —
essentially no relationship, despite the LLM producing real score
variance on this dimension (unlike the initial degenerate run). This
result is reported as-is rather than explained away: a follow-up look
at the Communication feedback text and answer templates didn't surface
an obvious cause, and further speculation without more data would be
unfounded. This is flagged as an open question rather than a solved one.

## Limitations

- **Small sample.** 15 interviews (75 scored pairs), with only 2
  strong-tier and 3 weak-tier interviews existing in the entire
  synthetic dataset. Rank correlations above are based on limited
  variation and should be read as directional, not precise.
- **Synthetic reference scores are not ground truth.** They were
  generated independently of the answer text (see above) and were never
  validated by a human rater. Agreement or disagreement with them shows
  how an LLM score compares to *this specific synthetic process* — not
  whether the LLM would accurately evaluate a real candidate.
- **Limited answer template diversity.** Each tier/competency has 2-3
  hand-written templates, not naturally-written unique answers per
  candidate, so within-tier score variation partly reflects template
  reuse rather than individual differences.
- **No independent human scoring.** A small human-scored sample
  (20-30 answers) would substantially strengthen this experiment by
  giving a genuine reference point independent of both the LLM and the
  synthetic generation process. Not done here due to time constraints.
- **Single scoring run.** Each answer was scored once. Consistency
  across repeated runs on the same answer was not tested.
- **Free-tier model constraints.** The model name and daily/per-minute
  quotas changed multiple times during this project (see
  `llm_score_interviews.py`), which shaped practical choices like
  sample size and request pacing — a real-world consideration for
  anyone building on free-tier LLM APIs, not just an implementation
  detail.

## Conclusion

This experiment doesn't establish that an LLM can replace structured
interview scoring, and it isn't designed to. What it does show is a
reproducible pipeline for testing LLM-based scoring against a defined
rubric, and a concrete, non-obvious finding: an LLM can be systematically
miscalibrated in absolute terms while still preserving useful relative
ranking on most dimensions — with at least one dimension (Communication)
where even that broke down, for reasons this experiment couldn't fully
explain with the data available.
