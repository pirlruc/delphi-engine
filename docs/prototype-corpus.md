# Prototype corpus field

This is **not** an ADR file. The decision record is Epic [SYS-009](issues.yml).
Implementation of [PROTO-003](issues.yml) stays blocked until that Epic names a field.

## What “field” means here

It is **not** a form field, a database column, or “computer science vs patents.”

It is the **slice of the world’s literature we download first** so the prototype has a
dense enough graph to:

1. Extract a user PDF into categories/subcategories.
2. Answer “what is the next research path?” and “what is a patent opportunity?”
   inside those categories.
3. Hindcast: hide a real historical paper or patent and see if Prometheus
   reconstructs it from only earlier work.

Catalogs such as OpenAlex nest works roughly as:

```text
domain  →  field  →  subfield  →  topic
example: Health Sciences → Biotechnology → Gene editing → CRISPR-Cas9
```

Patents nest by CPC (example: C12N 15/11 — genetic engineering).
The prototype maps both into the same Category/Subcategory query model
([SYS-008](issues.yml)).

A “field” for us is **one such neighborhood** (OpenAlex field or subfield **plus**
the CPC classes that patent that neighborhood), not the whole planet.

## Why we cannot ingest “everything” first

Hindcasting needs **local density**: many papers that cite each other in the
same area, with dates. A thin random sample of all science produces empty
neighborhoods and fake scores. Billion-scale ingest is Phase 3
([SCALE-001](issues.yml)).

The field you pick also decides whether the dual audience works:

| Audience | Needs from the slice |
| --- | --- |
| Working scientist | Recent papers, methods, “what to try next” |
| Patent searcher | Claims, CPC classes, “where is the whitespace” |

A papers-only ML slice serves scientists and starves patent searchers.
A patent-only CPC dump does the reverse. The prototype field must have **both**.

## What a good first field looks like

- Public paper metadata (OpenAlex) **and** public patent metadata (PatentsView/USPTO) exist.
- There is at least one famous historical leap we can hide for hindcasting
  (a paper **or** a patent family).
- Categories/subcategories are meaningful (not one giant “miscellaneous”).
- A typical user PDF is a paper or an application, not a 400-page textbook.

## Candidates (owner picks one)

These are examples, not a ranking. Say which one (or name another).

| Candidate | Why it fits both users | Hindcast hook (illustrative) | Risk |
| --- | --- | --- | --- |
| Gene editing / CRISPR | Dense papers **and** famous patent disputes | Hide a foundational Cas9 paper or the associated patent family | Bio jargon; some full texts are paywalled (we still have metadata + the user PDF) |
| mRNA vaccines / LNPs | Papers plus a thick patent landscape | Hide an early LNP or nucleoside-modification paper/patent | Fast-moving; leakage via the LLM’s prior knowledge is a real eval risk |
| Lithium-ion / solid-state batteries | Materials papers + CPC H01M | Hide a well-known electrolyte or anode paper | Figures/tables in PDFs are harder to extract |
| Perovskite photovoltaics | Academic + industrial patenting | Hide an early perovskite solar-cell paper | Smaller graph than CRISPR/ML |
| Transformer / foundation models | Enormous paper graph | Hide “Attention Is All You Need” or a later scaling paper | Patent coverage is weaker than the paper graph; worse for the patent-searcher path |

Computer-science machine learning was the previous default. It is a **weak** default
now that the prototype must return **patent** suggestions as well as research paths.

## What we will ingest once you name it

For that one neighborhood only:

- OpenAlex works + citation edges + topic assignments.
- A matching PatentsView/USPTO slice (CPC classes you confirm).
- User PDFs you consent to upload, extracted into the same category tree.

Not: all of arXiv, all of USPTO, or a second unrelated domain.

## Status

**Unresolved.** Do not start [PROTO-003](issues.yml) until [SYS-009](issues.yml)
records the chosen field name, OpenAlex filter, and CPC (or equivalent) filter.
