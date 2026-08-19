# Changelog

All notable changes to this package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- FastAPI walking skeleton: batch-check, neighborhood (citation/content/union), consented PDF upload, and generate.
- In-memory catalog with `cites` and `similar_to` edges. Postgres/pgvector remains compose-only until SCALE-001.
- PDF upload is idempotent on content hash.
