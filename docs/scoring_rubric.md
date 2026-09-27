# Interview Scoring Rubric (v1)

Used to score candidate interview answers, both in the synthetic data
generation (`generate_data.py` / `generate_transcripts.py`) and by the
Gemini-based scoring experiment (`llm_scoring.py`). Scores are 0-100 per
dimension. The three bands below describe what a score in that range
should reflect; they are guidance for a human or an LLM scorer, not
hard thresholds.

Dimensions were taken directly from the project's existing
`interview_scores` table — Communication, Technical Depth, Problem
Solving, Role Fit, Ownership — rather than invented separately for the
LLM step, so the reference scores and the LLM scores are evaluating
the same construct.

### Scoring principles

- Score each dimension independently. Strength in one dimension should not
  compensate for weakness or lack of evidence in another.
- Score only the evidence contained in the candidate's answer. Do not infer
  unstated experience, qualifications, intent, or personality traits.
- If an answer provides insufficient evidence to support a high score, score
  based on the evidence available rather than filling in missing information.
- The Low/Medium/High bands are qualitative anchors, not keyword-based
  classification rules. Scores within each band should reflect the strength,
  specificity, and completeness of the evidence.

| Dimension | Low (0–40) | Medium (41–75) | High (76–100) |
|---|---|---|---|
| **Communication** | Answer is unclear, rambling, or hard to follow; jargon used without explanation | Gets the point across but lacks structure or a concrete example | Clear, well-structured, uses a concrete example suited to the audience |
| **Technical Depth** | Vague or incorrect approach; no reasoning given | A workable approach is described but without discussing trade-offs | Sound approach with reasoning about why, including trade-offs or edge cases |
| **Problem Solving** | No clear method; relies on someone else to resolve it | A reasonable but ad-hoc approach to the problem | Structured approach: diagnosis, fix, and a step to prevent recurrence |
| **Role Fit** | Generic or unrelated motivation, no link to the role's actual work | Plausible interest, some connection to relevant experience | Clear, specific connection between their background and this role's requirements |
| **Ownership** | No example given, or deflects responsibility | Acknowledges a mistake but with limited detail on the response | Concrete example of taking responsibility and acting on it without being asked |

## Notes on use

- **Reference scores are not ground truth.** The `interview_scores` table
  used for comparison is itself synthetically generated (see
  `generate_data.py` / `generate_transcripts.py`), not independently
  verified human judgment. Agreement between the LLM and these reference
  scores shows how closely an LLM reproduces *this specific rubric applied
  to synthetic data* — not that the LLM evaluates real candidates
  accurately. See `docs/methodology.md` (to be written) for the full
  discussion of this limitation.
- **Prompt versioning:** this rubric is `prompt_v1`. If the wording sent
  to the LLM changes in a way that could affect scores, it becomes
  `prompt_v2`, and both are kept so results can be compared — not to
  chase higher agreement with the reference scores, but to make the
  experiment's history traceable.
