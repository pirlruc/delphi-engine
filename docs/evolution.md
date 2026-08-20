# Evolution notes — models, embeddings, JEPA

This is **not** an ADR and **not** a second decision log. Locked product decisions stay in
[`docs/issues.yml`](issues.yml) epics (SYS-006, SYS-010, PROD-003). This file is the lab notebook
for *which models to try* and *how to build the text that is embedded*.

Recorded: 2026-08-20.

The Google AI Mode share
([share.google/aimode/2uXpUaEY4y9sTOpMa](https://share.google/aimode/2uXpUaEY4y9sTOpMa))
is a JavaScript snapshot and could not be fetched as text from this environment. The embedding
rules below are the established paper/patent practice that write-up class typically repeats
(SPECTER/SPECTER2, SciRepEval, patent claim embeddings), applied to Delphi’s **one mixed
paper+patent content graph**.

## Delphi uses four model jobs

| Role | Code | Interface | What “good” means |
| --- | --- | --- | --- |
| **Extract** | `daedalus.extract` | chat + JSON | Bibliographic fields, no invented DOIs |
| **Generate** | `delphi_prometheus` | chat + JSON | Grounded in a **masked** neighborhood |
| **Judge** | `epimetheus.score` | chat + JSON, 1–5 | Rubric, not “I have seen this paper” |
| **Embed** | `daedalus.embed` | `/embeddings` | `similar_to` stays in-subcategory |

SYS-006 already splits chat vs embed: `DELPHI_LLM_MODEL` and `DELPHI_LLM_EMBEDDING_MODEL`.
Tests stay on Fake. EvalRun must record adapter + model id.

## Recommended models (reviewed for a mixed paper/patent graph)

### Chat (extract / generate / judge)

| Role | First live test | Stronger follow-up | Why |
| --- | --- | --- | --- |
| Extract | `gpt-4o-mini` (SYS-006 cloud default) | Claude Sonnet or Gemini Flash | JSON mode, cheap, OpenAI-compatible adapter |
| Generate | Claude Sonnet **or** GPT-4.1-class | Gemini Pro if neighborhoods are long | Technical/patent phrasing; less generic FM essay |
| Judge | **A different checkpoint than generate** | Same family is fine | Hindcast leakage if the generator grades itself |

Do not start with a frontier “best overall” chat model. The go/no-go is leak-proof hindcasting
on codes/stego (SYS-009), not fluency.

### Embeddings (content graph)

Delphi k-NN is **one vector space for papers and patents**. That constraint outranks
paper-only or patent-only specialists.

| Priority | Model | Why |
| --- | --- | --- |
| **1 — first live** | OpenAI `text-embedding-3-small` (default) | Cheap, OpenAI-compatible, English CS+patents is enough to see if `similar_to` is junk |
| **2 — if neighborhoods are keyword-shallow** | `text-embedding-3-large` or Google `gemini-embedding-001` | Instruction/task-type embedders; Gemini’s `task_type` helps retrieval |
| **2b — patent-heavy slice** | Voyage 3.5 / Voyage law-adjacent | Often stronger on legal/technical retrieval than generic OpenAI-small |
| **Later, local only** | SPECTER2 proximity (papers) or PaECTER / PatentSBERTa (patents) | Citation-informed **scientific** or **patent** spaces. Using either alone would distort the other kind in the **same** k-NN. Only try after measuring the general embedder, or as a fused/extra signal (PROD-003), not as the Phase 1 space |
| **Not for this graph** | Separate paper space + patent space | Breaks `mode=content` union queries |
| **Not for Phase 1** | JEPA / V-JEPA / LLM-JEPA as the embedder | See below |

Keep **one** embedding model id in a catalog. Mixing `3-small` and `3-large` vectors makes cosine meaningless.

### Where JEPA is a good alternative

JEPA (I-JEPA, V-JEPA, LLM-JEPA training papers) predicts **in latent space**, not JSON.
It is **not** a replacement for extract, generate, or judge, and there is no
`DELPHI_LLM_MODEL=jepa` on the OpenAI-compatible adapter.

Consider JEPA **only** for the content-graph encoder, and only when all of these hold:

1. Title+abstract+CPC (and claims when present) with a general embedder has been measured and is the bottleneck (empty or FM-dominated `similar_to`).
2. The job is “predict the representation of related work in this subcategory,” not “write a path proposal.”
3. Papers and patents still land in **one** space (a JEPA trained only on papers has the same split-space problem as SPECTER2).
4. V-JEPA / vision JEPA is in scope only if we embed **figures or page images**. The current pipeline embeds extracted **text**.

LLM-JEPA is a **training objective** for Llama/Gemma-class models, not a hosted patent API.
Follow-up work reports weak coupling between prettier hidden geometry and decoded task accuracy —
do not assume a JEPA finetune improves hindcast scores.

Until then, JEPA stays research (PROD-003 / later), not the prototype provider.

## How to embed a paper or a patent (what we treat as valid)

Valid (implemented in `daedalus.embed.compose_embed_text` / `HashEmbedder`):

1. **Do not embed raw PDF bytes.** Use structured text.
2. **Document unit is title + separator + abstract**, not the bibliography or citation dump (SPECTER2 input shape).
3. **Patents add CPC/keywords** (and claims when the ingest record has them). Claims carry the invention; abstracts are often marketing.
4. **Uploads may add extracted body**, truncated so methods/claims-like text wins over references.
5. **Instruction prefix by kind** (`Represent this scientific paper…` / `Represent this patent…`) so instruction-tuned embedders (Gemini, e5-instruct, Voyage) know the task. Harmless for others.
6. **One vector per work.** If text exceeds the window, **chunk and mean-pool** — do not drop the title/abstract head.
7. **Skip extra text that is only title+abstract** so old call sites do not duplicate fields.
8. **Same model for every work in the slice.**

Rejected for Phase 1:

- SPECTER2-only or PatentSBERTa-only as the production space (mixed corpus).
- ColBERT multi-vector store (SCALE-001 territory).
- Embedding full OCR including references.
- JEPA as the cloud chat model.
- Two embedding models in one `similar_to` table.

## Prototype cost (order of magnitude, list prices ~Aug 2026)

Assumes the **walking-skeleton loop**: 8 fixture works, 1 consented PDF, 2 generate calls,
a handful of judge trials; optionally a **small live slice** (~5 works × 4 subcategories papers,
and the same cap for patents).

Unit rates used (public list, input/output per 1M tokens unless noted):

- OpenAI `gpt-4o-mini`: about **$0.15 / $0.60**
- OpenAI `text-embedding-3-small`: **$0.02** (input only)
- OpenAI `text-embedding-3-large`: **$0.13** (input only)
- Claude Sonnet 5: about **$2 / $10** (order of magnitude above mini; Sonnet 4.6 is ~$3 / $15)

A title+abstract (+ claims) is a few hundred tokens. Fifty catalog works at `3-small` is
well under a cent. Chat (extract, generate, judge) is the spend that moves.

| Spend | Mini + `3-small` (recommended first) | Sonnet + `3-large` / Gemini embed |
| --- | --- | --- |
| Embed ~50 short docs | < $0.01 | < $0.05 |
| Extract + 2 generate + ~4 judge | ~ $0.01–0.05 | ~ $0.20–1.00 |
| A week of local tinkering | **$1–5** | **$5–30** |
| Tens-of-thousands ingest (PROTO-003) | Embeddings dominate: tens of dollars at `3-small`, low hundreds at large/Voyage | Chat is still the expensive part if you re-extract every PDF |

Chat tokens are the lever. Embeddings are cheap until catalog scale. The Fake + fixture
demo is **$0**.

## Other APIs for the prototype

| API | Need it to run the demo? | Typical cost | What to do |
| --- | --- | --- | --- |
| **Nothing (fixture + Fake LLM)** | **No — this is the default** | $0 | `bash scripts/demo-prototype.sh` |
| OpenAlex | Only for `daedalus --live` | $0 | Set `DELPHI_MAILTO` |
| PatentsView | Only for live USPTO pages | $0 with key | `PATENTSVIEW_API_KEY` |
| EPO OPS | Optional EP patents | $0 with weekly quota | `EPO_OPS_KEY` + `EPO_OPS_SECRET` |
| Lens.org | Optional multi-office | $0 at modest volume | `LENS_API_TOKEN` |
| WIPO PATENTSCOPE | No | Paid SOAP; we only hit a JSON gateway if you have one | Skip |
| PatSnap | No | Commercial (often large annual) | Skip until a paid seat exists |
| Postgres 16 | Only if you want SQL persist | $0 on your Docker host | `bash scripts/compose-up.sh` |
| Cloud LLM | Only for a non-Fake hindcast | See table above | `DELPHI_LLM_KIND=cloud` + API key |

The prototype is designed so **zero paid APIs** are required. Extra keys buy a wider patent
neighborhood, not a working loop.

## Steps on your machine (and why)

1. **Keep Fake + fixture for the first run** — proves extract → dual graphs → both generate kinds → hindcast without keys or spend.
2. **Install Docker and run `bash scripts/compose-up.sh`** — this VM has no Docker; Postgres persist is verified on your host.
3. **Copy `.env.example` → `.env` and set `DELPHI_MAILTO`** — polite OpenAlex pool; Compose reads `.env`.
4. **Add `DELPHI_LLM_API_KEY` and `DELPHI_LLM_KIND=cloud` only when you want a real extract/generate/judge** — still leave embeddings on `text-embedding-3-small` until `similar_to` looks wrong.
5. **Register PatentsView and/or EPO (free) if you want live patents; skip PatSnap/WIPO** — USPTO+EPO+Lens is enough to see multi-office identity; commercial APIs are not the bottleneck.
6. **Use a second model id for the judge** when you score a hindcast you care about — otherwise you are grading the generator’s style.
7. **Do not point the catalog at SPECTER2 or JEPA yet** — mixed graph, no hosted JEPA adapter, measure the general embedder first.

## Code map

| Piece | Path |
| --- | --- |
| Compose embed text, chunk mean-pool | `daedalus/src/daedalus/embed.py` |
| Provider defaults | `contracts/src/delphi_contracts/llm.py` `provider_settings_from_env` |
| Dual-graph rules | [`docs/prototype-graphs.md`](prototype-graphs.md) |
| Product backlog | [`docs/issues.yml`](issues.yml) PROD-003 (richer claims/sections) |
