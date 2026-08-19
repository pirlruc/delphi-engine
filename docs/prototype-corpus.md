# Prototype corpus

This is **not** an ADR file. The decision record is Epic [SYS-009](issues.yml).

## Decision (owner, 2026-08-19)

The first corpus is **one computer-science neighborhood with four subcategories**,
chosen because the owner will actually use the prototype:

| Subcategory id | Label | Role |
| --- | --- | --- |
| `transformers_foundation_models` | Transformers / foundation models | Methods the owner may apply, plus a bounded FM paper/patent slice |
| `computer_vision` | Computer vision | Visual pipeline around codes and hiding; **not** all of cs.CV |
| `steganography` | Steganography / watermarking / information hiding | Niche graph; good hindcast target (less memorized than “Attention Is All You Need”) |
| `two_d_codes` | 2D codes (QR, Data Matrix, Aztec, barcodes) | Strongest patent landscape of the four |

Treat these as **filters on one ingest**, not four products. Category/subcategory
queries ([SYS-008](issues.yml)) are how a 2D-code question avoids drowning in LLM papers.

## Why this is a good choice for this prototype

- **You will run it.** A CRISPR slice that nobody uploads PDFs into is a worse prototype.
- **The three visual topics cohere.** CV + 2D codes + steganography is a real intersection
  (machine-readable imagery, print/camera pipeline, hiding or authenticating payloads).
  Foundation models sit beside that as *methods* (“what architecture to try on my decoder”).
- **Patent-searcher path is not empty.** 2D codes and watermarking/CV have CPC homes
  (`G06K`, `G06V`, `G06T`). Transformers-alone would have been the weak patent slice;
  pairing it with codes/stego fixes that.
- **Hindcasting can avoid the worst leakage.** Do not use “Attention Is All You Need” as
  the only held-out paper; cloud and local FMs have seen it. Prefer a 2D-code, watermarking,
  or mid-2010s stego paper/patent family.

## Why it can go badly (and the mitigations)

| Risk | What happens | Mitigation |
| --- | --- | --- |
| Unbounded computer vision | Ingest becomes ImageNet/detection/medical/AV and blows the budget | Bound `computer_vision` to topics that intersect representation learning, document/camera capture, and machine-readable marks — not driving, not radiology unless later named |
| Transformers drown the niche | Embeddings and “next path” ignore QR/stego | Hard cap per subcategory; generate **requires** category/subcategory; never query the union unlabeled |
| Four slices, weak edges | Stego papers do not cite FM papers, neighborhoods look empty | Allow semantic neighbors later (PROD-003); for Phase 1, evaluate **inside** a subcategory first |
| FM patent noise | CPC `G06N` is huge and messy | Prefer `G06K 7/` / `G06K 19/` (readers and record carriers) and watermarking/security codes; add `G06N` only with keyword intersection (transformer, vision transformer, foundation model) |
| LLM look-ahead on famous FM papers | Hindcast scores are fake | Held-out set prefers codes/stego/CV; record model name on EvalRun ([SYS-006](issues.yml)) |

## Starting filters (refine in PROTO-003)

Paper side (OpenAlex / arXiv), **intersection or keyword**, not “all of these cs.* classes”:

- Transformers / FMs: arXiv `cs.LG`, `cs.CL`, `cs.AI` with topic/keyword transformer, foundation model, vision transformer, LLM. **Cap** so this is not larger than the other three combined.
- Computer vision: arXiv `cs.CV` **restricted** to topics near document images, camera capture, representation learning for recognition — exclude autonomous driving and medical imaging unless added later.
- Steganography: keywords steganography, steganalysis, watermarking, information hiding; venues/topics under `cs.CR` / `cs.MM`.
- 2D codes: keywords QR, “data matrix”, “2D barcode”, Aztec, PDF417, “machine readable code”.

Patent side (CPC prefixes to start, then keyword AND):

- `G06K 7/` data readers; `G06K 19/` record carriers (QR/Data Matrix/barcodes)
- `G06V` image recognition (bounded by code/stego/document keywords)
- `G06T` image processing (same keyword bound)
- `G06N` only with transformer / foundation-model / ViT keywords
- Security/hiding: watermark / steganograph* in title/abstract; do not dump all of `G06F 21/` or `H04L 9/`

Numeric caps land in Daedalus config during PROTO-003 (suggested starting cap: tens of thousands of works **per subcategory**, transformers not allowed to exceed the sum of the other three).

## What we ingest

- OpenAlex works + citation edges + topic assignments for the four subcategories.
- Matching PatentsView/USPTO rows under the CPC/keyword bounds above.
- User PDFs consented for upload, classified into these four (plus `other` if the extractor is unsure — `other` is not a generate target until confirmed).

Not: all of arXiv, all of USPTO, medical CV, or a second scientific domain.

## Status

**Named.** [PROTO-003](issues.yml) may start against these filters. Caps and exact OpenAlex concept IDs are implementation detail in Daedalus, not a second decision log.
