"""Daedalus CLI: ingest the fixture slice or map HTTP JSON pages."""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx

from daedalus.fetch import fetch_openalex, fetch_patentsview
from daedalus.ingest import load_fixture

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args.

    Args:
        argv: Optional CLI args.

    Returns:
        Exit code. Prints the number of records that would be ingested.
    """
    parser = argparse.ArgumentParser(description="Daedalus ingest")
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--openalex-url", default=None)
    parser.add_argument("--patentsview-url", default=None)
    parser.add_argument("--subcategory", default="two_d_codes")
    args = parser.parse_args(argv)
    if args.openalex_url:
        with httpx.Client() as client:
            records = fetch_openalex(args.openalex_url, args.subcategory, client)
        print(len(records))
        return 0
    if args.patentsview_url:
        with httpx.Client() as client:
            records = fetch_patentsview(args.patentsview_url, args.subcategory, client)
        print(len(records))
        return 0
    records = load_fixture(args.fixture)
    print(len(records))
    if args.dry_run:
        return 0
    return 0
