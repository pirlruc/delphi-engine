# Eval rubric (Fake and live judges)

Used by Epimetheus LLM-as-judge ([PROTO-005](issues.yml), [SYS-006](issues.yml)). Scores are integers 1–5.

| Score | Novelty | Relevance | Accuracy |
| --- | --- | --- | --- |
| 1 | Restates the seed | Off-topic for the subcategory | Contradicts the held-out work |
| 3 | Incremental step a reviewer would expect | Same subcategory, plausible next experiment | Partial overlap with what happened |
| 5 | Non-obvious given only the masked past | Directly answers the research_path or patent_whitespace query | Close match to the held-out title/claims |

Embedding similarity is cosine of proposal text vs held-out title+abstract, recorded on `EvalRun` alongside the adapter and model id. The Fake provider always returns 4/4/4 so tests are deterministic; live cloud/local judges must still see a leak-proof `MaskedContext`.
