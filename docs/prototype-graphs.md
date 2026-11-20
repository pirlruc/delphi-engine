# Prototype graphs

This is **not** an ADR file. The decision record is Epic [SYS-010](issues.yml).

After a consented PDF upload, the prototype must:

1. **Extract bibliographic metadata** from that PDF: title, authors, keywords, dates, identifiers if present, and other structured fields the extractor can support.
2. **Build a citation graph** around it: directed `cites` edges from the bibliography (and from catalog citation data for other works).
3. **Build a content graph** around it: similarity edges from the **text of this paper** compared with the **text of other papers** already in the slice (not citations alone).

Path and patent queries use both neighborhoods, filtered by subcategory ([SYS-008](issues.yml), [SYS-009](issues.yml)). Temporal masks apply to **both** graphs ([PROTO-005](issues.yml)).

## Citation graph

| Source | What we store |
| --- | --- |
| OpenAlex / PatentsView / EPO / WIPO / PatSnap / Lens ingest | Work nodes plus the citation/continuation edges those APIs provide |
| Uploaded PDF | Bibliography entries extracted from the PDF, matched to catalog works via identity (DOI, title+year, …). Unmatched cites stay as unresolved identities |

Edges are directed: `from_work` cites `to_work`. Dates on nodes make hindcasting possible.

## Content graph

Citation links miss papers that are about the same method but do not cite each other. The content graph is built in one embedding space:

| Work kind | Text used for the vector |
| --- | --- |
| Catalog paper | Title + abstract + identifiers + topic keywords, with a retrieval instruction prefix |
| Catalog patent | Title + abstract + identifiers + CPC/keywords + **capped** claims (first three, clipped) |
| Uploaded PDF | Catalog fields plus extracted body (truncated / contextual-chunk mean-pooled). Not raw PDF bytes |

Title and abstract are the mixed-graph bridge (papers have no claims). Kind-specific prefixes and contextual mean-pooling live in `daedalus.embed` ([docs/evolution.md](evolution.md)). Licensed full text and a hybrid lexical index wait for [PROD-003](issues.yml).

Each work gets one embedding. The content graph is the **top-k nearest neighbors** among other works in the same prototype slice (and optionally the same subcategory). Those neighbors are stored as `similar_to` edges with a score so Hermes can show them.

The uploaded paper is **not** a graph of only its own tokens. Its content edges exist only relative to **other** works already ingested.

## What a neighborhood query returns

`mode=citation | content | union` ([PROTO-002](issues.yml), [PROTO-009](issues.yml)):

- **citation** — inbound/outbound `cites` within the subcategory and time bound
- **content** — top-k `similar_to` neighbors that pass the same time and subcategory filters
- **union** — both, tagged by edge kind so Prometheus can tell them apart

## Masking

A later paper that is semantically close is still **future**. Epimetheus must drop content-graph neighbors with publication date after the mask instant, not only citation descendants.

## Store

Both graphs live in Postgres in Phase 1: an edge table for `cites` and `similar_to`, vectors in pgvector ([SYS-002](issues.yml)). Split engines wait for [SCALE-001](issues.yml).
