# Changelog

All notable changes to this package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- SYS-009 fixture ingest (eight works across four subcategories) with caps and CV blocklist.
- OpenAlex and PatentsView record mappers.
- PDF extraction via SYS-006 (Fake in tests) and hash embeddings that write `similar_to` against other works.
- Sample demo PDF, LLM extract retries, and OpenAlex/PatentsView HTTP fetch with retry and poison skip.
- Live OpenAlex paging for the four SYS-009 subcategories (`daedalus --live`); authorships, inverted abstracts, and referenced_works mapping.
- Patent fetchers for EPO OPS, WIPO JSON, PatSnap, and Lens.org (`daedalus --live-patents`).
- Canonical embed text (title/abstract/CPC/claims, instruction prefix, chunk mean-pool).
