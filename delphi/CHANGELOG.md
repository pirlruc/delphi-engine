# Changelog

All notable changes to this package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- FastAPI walking skeleton: batch-check, neighborhood (citation/content/union), consented PDF upload, generate, and `/health`.
- In-memory catalog plus `PostgresCatalog` (DSN via `DELPHI_DATABASE_URL` / Compose).
- PDF upload is idempotent on content hash; a second upload re-matches bibliography and re-embeds.
- Identity index drops stale keys on upsert; DOI/patent values are canonicalized. Content-graph k-NN compares one embedding model and rebuilds all `similar_to` edges after each embed.
