#!/usr/bin/env python3
"""Composition root for the walking-skeleton prototype (memory catalog + Fake LLM)."""

from __future__ import annotations

import argparse

import uvicorn

from daedalus.embed import HashEmbedder
from daedalus.extract import PdfExtractor
from daedalus.ingest import ingest_records, load_fixture
from delphi.app import AppContainer, create_app
from delphi.catalog import MemoryCatalog
from delphi_prometheus import PathGenerator


def build_container() -> AppContainer:
    """Wire catalog, fixture ingest, extractor, embedder, and generator.

    Returns:
        FastAPI collaborators.
    """
    catalog = MemoryCatalog()
    ingest_records(catalog, load_fixture())
    embedder = HashEmbedder(catalog)
    for work in catalog.list_works():
        embedder.embed_and_link(work, f"{work.title} {work.abstract}")
    return AppContainer(
        catalog=catalog,
        extractor=PdfExtractor(),
        embedder=embedder,
        generator=PathGenerator(),
    )


def main(argv: list[str] | None = None) -> int:
    """Serve the prototype API.

    Args:
        argv: Optional CLI args.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(description="Delphi prototype (in-memory)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    uvicorn.run(create_app(build_container()), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
