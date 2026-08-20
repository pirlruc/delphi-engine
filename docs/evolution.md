# Evolution notes — models, embeddings, JEPA

This is **not** an ADR and **not** a second decision log. Locked product decisions stay in
[`docs/issues.yml`](issues.yml) epics (SYS-006, SYS-010, PROD-003). This file is the lab notebook
for *which models to try* and *how to build the text that is embedded*.

Recorded: 2026-08-20. Updated the same day after the Google AI Mode transcript on
paper/patent embeddings and JEPA was pasted in full
([share.google/aimode/2uXpUaEY4y9sTOpMa](https://share.google/aimode/2uXpUaEY4y9sTOpMa)).

That write-up is generic **search/RAG** advice (query → ranked documents, hybrid BM25,
cross-encoder rerank). Delphi’s content graph is **symmetric work-to-work k-NN** in
**one mixed paper+patent space**, used to ground generate/hindcast — not a prior-art
search engine. Below, keep only what survives that constraint.

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
paper-only or patent-only specialists. PatenTEB-style results (general bi-encoders often
beat older domain models **if** the text is composed well) match that: start general,
measure, then specialize.

| Priority | Model | Why |
| --- | --- | --- |
| **1 — first live** | OpenAI `text-embedding-3-small` (default) | Cheap, OpenAI-compatible, 8k is enough for title+abstract+capped claims. Enough to see if `similar_to` is junk |
| **2 — technical mixed corpus** | Voyage `voyage-3-large` (OpenAI-compatible base URL) | Write-up’s best commercial fit for technical/legal language and paper-abstract ↔ patent-claim matching. Use when `3-small` neighborhoods are keyword-shallow |
| **2 — high volume / MRL** | OpenAI `text-embedding-3-large` | Safe baseline at catalog scale; Matryoshka dims can shrink pgvector later (not wired in Phase 1) |
| **2 — long methods sections** | Gemini Embedding 2 / `gemini-embedding-001` | 32k window if we start embedding more than abstract+claims. Prototype text is short, so this is not the first knob |
| **Local (same adapter)** | Qwen3 Embedding 8B behind `DELPHI_LLM_KIND=local` | Strong open-weight technical embedder, 32k context, no token bill. Fits the existing OpenAI-compatible local path |
| **Later, not Phase 1 space** | BGE-M3 | Dense **plus sparse** in one model — valuable for patent numbers, DOIs, formulas. Needs a hybrid index Delphi does not have yet (stored cosine k-NN only) |
| **Later, not Phase 1 space** | SPECTER2 / PaECTER / PatentSBERTa / Patembed | Paper-only or patent-only spaces. Using any of them **alone** distorts the other kind in the same k-NN |
| **Not this graph’s job** | Cohere Embed v4 + Rerank | Optimized for **short query vs long document**. `similar_to` is work↔work (two abstracts/claims), not a search box. Revisit if Hermes grows a user search UI |
| **Not for this graph** | Separate paper space + patent space | Breaks `mode=content` union queries |
| **Not for paper/patent retrieval** | JEPA / V-JEPA / LLM-JEPA / VL-JEPA | See below |

Keep **one** embedding model id in a catalog. Mixing `3-small` and `3-large` vectors makes cosine meaningless.

## JEPA is not a good alternative for this job

The earlier note left JEPA as a “maybe later encoder.” The paper/patent write-up is right to
close that door for **text retrieval**. JEPA (I-JEPA, V-JEPA, VL-JEPA) is a **world-model /
latent prediction** family: mask a patch or frame, predict the missing representation.
That is the wrong objective for Delphi’s content graph.

| Claim | Why it fails here |
| --- | --- |
| Wrong objective | We need a static vector of scientific/legal assertions, not “what happens next in a scene” |
| Surface details are the signal | Chemical tokens, claim numbers, CPC codes, gene-like strings, QR/stego terms. JEPA is trained to throw those away as noise; missing one digit ruins prior-art style matching |
| No hosted text encoder | There is no `DELPHI_LLM_MODEL=jepa` on the OpenAI-compatible adapter. Text-JEPA papers are niche logic projects, not trillion-token academic/patent vocabularies |
| Mixed graph | A vision JEPA on figures would be a **second** modality, not a drop-in for `similar_to` |

Do **not** consider JEPA as the catalog embedder, even after measuring `3-small`. If figures
or page images are added later, V-JEPA/VL-JEPA could be an **extra** signal beside the text
vector — still not a replacement for a contrastive bi-encoder.

What to use instead of JEPA (same as the write-up’s stack, mapped to Delphi):

1. **Bi-encoder** for ingest (`3-small` → Voyage-large or Qwen3-8B local).
2. **Cross-encoder rerank** only if we add query-time search (Hermes). Stored top-k `similar_to` does not rerank at generate time in Phase 1.
3. **Hybrid dense+BM25** later (BGE-M3 or pgvector + a lexical index) so DOI/patent numbers cannot disappear. Identifiers are already copied into the embed string; that is a weak substitute, not a sparse index.

## How to embed a paper or a patent (what we treat as valid)

Valid (implemented in `daedalus.embed`):

1. **Do not embed raw PDF bytes.** Use structured text.
2. **Semantic core is title + abstract** (SPECTER2 shape). That is the **bridge** between papers and patents in one space. Patent-retrieval studies that prefer abstracts over full claim dumps for *semantic* match apply even more here, because papers have no claims.
3. **Patents add CPC/keywords and a capped claim block** (first three claims, clipped). Claims carry the invention; uncapped legalese drowns the abstract and pulls patents away from papers.
4. **Public identifiers (DOI, arXiv, patent number) go in the header** so those tokens are in the dense vector. This is not a substitute for BM25.
5. **Uploads may add extracted body**, truncated. Bibliography/references stay out of the core.
6. **Instruction prefix by kind** so instruction-tuned embedders (Gemini, e5-instruct, Voyage) know the task.
7. **One vector per work.** If text exceeds the window, **contextual chunk + mean-pool**: every window repeats title (and abstract/CPC header). Do not embed a methods chunk with no title.
8. **Skip extra text that is only title+abstract** so old call sites do not duplicate fields.
9. **Same model for every work in the slice.**

Rejected for Phase 1:

- SPECTER2-only, PatentSBERTa-only, or Patembed-only as the production space (mixed corpus).
- ColBERT multi-vector store (SCALE-001 territory).
- Embedding full OCR including references.
- Uncapped claim dumps as the patent vector.
- JEPA as chat model or as the catalog embedder.
- Two embedding models in one `similar_to` table.
- Hybrid BM25 / Cohere rerank as a requirement to run the prototype (no search UI; cosine k-NN on ~tens of works).

## Prototype cost (order of magnitude, list prices ~Aug 2026)

Assumes the **walking-skeleton loop**: 8 fixture works, 1 consented PDF, 2 generate calls,
a handful of judge trials; optionally a **small live slice** (~5 works × 4 subcategories papers,
and the same cap for patents).

Unit rates used (public list, input/output per 1M tokens unless noted):

- OpenAI `gpt-4o-mini`: about **$0.15 / $0.60**
- OpenAI `text-embedding-3-small`: **$0.02** (input only)
- OpenAI `text-embedding-3-large`: **$0.13** (input only)
- Claude Sonnet 5: about **$2 / $10** (order of magnitude above mini; Sonnet 4.6 is ~$3 / $15)

A title+abstract (+ capped claims) is a few hundred tokens. Fifty catalog works at `3-small` is
well under a cent. Chat (extract, generate, judge) is the spend that moves. Voyage-large and
Gemini embed are still cents at prototype scale; they matter at tens of thousands of docs.

| Spend | Mini + `3-small` (recommended first) | Sonnet + Voyage-large / `3-large` |
| --- | --- | --- |
| Embed ~50 short docs | < $0.01 | < $0.10 |
| Extract + 2 generate + ~4 judge | ~ $0.01–0.05 | ~ $0.20–1.00 |
| A week of local tinkering | **$1–5** | **$5–30** |
| Tens-of-thousands ingest (PROTO-003) | Embeddings dominate: tens of dollars at `3-small`, low hundreds at large/Voyage | Chat is still the expensive part if you re-extract every PDF |

Chat tokens are the lever. Embeddings are cheap until catalog scale. The Fake + fixture
demo is **$0**. Qwen3-8B local is **$0** API once the GPU/CPU box exists.

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
| Voyage / Gemini embed | No | Cents at prototype scale | Only after `3-small` looks shallow |
| Postgres 16 | Only if you want SQL persist | $0 on your Docker host | `bash scripts/compose-up.sh` |
| Cloud LLM | Only for a non-Fake hindcast | See table above | `DELPHI_LLM_KIND=cloud` + API key |

The prototype is designed so **zero paid APIs** are required. Extra keys buy a wider patent
neighborhood, not a working loop.

## Steps on your machine (and why)

1. **Keep Fake + fixture for the first run** — proves extract → dual graphs → both generate kinds → hindcast without keys or spend.
2. **Install Docker and run `bash scripts/compose-up.sh`** — this VM has no Docker; Postgres persist is verified on your host.
3. **Copy `.env.example` → `.env` and set `DELPHI_MAILTO`** — polite OpenAlex pool; Compose reads `.env`.
4. **Add `DELPHI_LLM_API_KEY` and `DELPHI_LLM_KIND=cloud` only when you want a real extract/generate/judge** — still leave embeddings on `text-embedding-3-small` until `similar_to` looks wrong.
5. **If neighborhoods stay keyword-shallow, switch embed to Voyage-large or local Qwen3-8B** — one model id for the whole catalog; re-embed after the switch.
6. **Register PatentsView and/or EPO (free) if you want live patents; skip PatSnap/WIPO** — USPTO+EPO+Lens is enough to see multi-office identity; commercial APIs are not the bottleneck.
7. **Use a second model id for the judge** when you score a hindcast you care about — otherwise you are grading the generator’s style.
8. **Do not point the catalog at SPECTER2, Patembed, or JEPA** — mixed graph, wrong objective (JEPA), measure a general bi-encoder first.

## Code map

| Piece | Path |
| --- | --- |
| Compose embed text, contextual chunks, mean-pool | `daedalus/src/daedalus/embed.py` |
| Provider defaults | `contracts/src/delphi_contracts/llm.py` `provider_settings_from_env` |
| Dual-graph rules | [`docs/prototype-graphs.md`](prototype-graphs.md) |
| Product backlog | [`docs/issues.yml`](issues.yml) PROD-003 (richer text / hybrid lexical) |
