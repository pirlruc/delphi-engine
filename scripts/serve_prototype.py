#!/usr/bin/env python3
"""Composition root: catalog (memory or Postgres), fixture ingest, SYS-006 LLM."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from delphi_contracts.json_tree import (
    as_dict,
    as_list,
    is_object_dict,
    is_object_list,
    namespace_dict,
    parse_json,
)
from delphi_contracts.llm import build_provider, provider_settings_from_env

from daedalus.embed import HashEmbedder
from daedalus.extract import PdfExtractor
from daedalus.ingest import ingest_records, load_fixture
from delphi.app import AppContainer, create_app
from delphi.postgres import catalog_from_url
from delphi_prometheus import PathGenerator


def build_container(
    database_url: str | None = None,
    records_path: Path | None = None,
    skip_fixture: bool = False,
) -> AppContainer:
    """Wire catalog, ingest, extractor, embedder, and generator.

    Args:
        database_url: Postgres DSN. None uses MemoryCatalog.
        records_path: Optional extra works JSON (list or {"works": [...]}).
        skip_fixture: Skip the packaged eight-work slice.

    Returns:
        FastAPI collaborators.
    """
    catalog = catalog_from_url(database_url)
    if not skip_fixture:
        ingest_records(catalog, load_fixture())
    if records_path is not None:
        payload = parse_json(records_path.read_text(encoding="utf-8"))
        if is_object_dict(payload) and "works" in payload:
            extra = [as_dict(item) for item in as_list(payload.get("works"))]
        elif is_object_list(payload):
            extra = [as_dict(item) for item in payload]
        else:
            extra = []
        ingest_records(catalog, extra)
    provider = build_provider(provider_settings_from_env())
    embedder = HashEmbedder(catalog, llm=provider)
    for work in catalog.list_works():
        embedder.embed_and_link(work)
    return AppContainer(
        catalog=catalog,
        extractor=PdfExtractor(provider),
        embedder=embedder,
        generator=PathGenerator(provider),
    )


def main(argv: list[str] | None = None) -> int:
    """Serve the prototype API.

    Args:
        argv: Optional CLI args.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(description="Delphi prototype API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DELPHI_DATABASE_URL"),
        help="Postgres DSN; unset keeps the in-memory catalog",
    )
    parser.add_argument("--records", type=Path, default=None)
    parser.add_argument("--skip-fixture", action="store_true")
    raw = namespace_dict(parser.parse_args(argv))
    database_url = raw.get("database_url")
    records = raw.get("records")
    host = raw.get("host")
    port = raw.get("port")
    uvicorn.run(
        create_app(
            build_container(
                database_url=database_url if isinstance(database_url, str) else None,
                records_path=records if isinstance(records, Path) else None,
                skip_fixture=raw.get("skip_fixture") is True,
            )
        ),
        host=host if isinstance(host, str) else "127.0.0.1",
        port=port if isinstance(port, int) and not isinstance(port, bool) else 8000,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
