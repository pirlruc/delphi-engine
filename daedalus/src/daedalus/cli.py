"""Daedalus CLI: ingest the fixture slice or map HTTP JSON pages."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import httpx

from daedalus.fetch import fetch_named_slice, fetch_openalex, fetch_patentsview
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
    parser.add_argument("--live", action="store_true", help="Fetch SYS-009 OpenAlex pages")
    parser.add_argument("--per-subcategory", type=int, default=25)
    parser.add_argument(
        "--mailto",
        default=os.environ.get("DELPHI_MAILTO", "delphi-engine@localhost"),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.openalex_url:
        with httpx.Client() as client:
            records = fetch_openalex(args.openalex_url, args.subcategory, client)
        return _emit(records, args.output)
    if args.patentsview_url:
        headers = _patentsview_headers()
        with httpx.Client(headers=headers) as client:
            records = fetch_patentsview(args.patentsview_url, args.subcategory, client)
        return _emit(records, args.output)
    if args.live:
        with httpx.Client(headers={"User-Agent": f"delphi-engine ({args.mailto})"}) as client:
            records = fetch_named_slice(
                client,
                per_subcategory=args.per_subcategory,
                mailto=args.mailto,
            )
        return _emit(records, args.output)
    records = load_fixture(args.fixture)
    print(len(records))
    if args.dry_run:
        return 0
    return 0


def _emit(records: list[dict[str, Any]], output: Path | None) -> int:
    """Print count and optionally write works JSON.

    Args:
        records: Ingest dicts.
        output: Optional JSON path.

    Returns:
        Exit code.
    """
    print(len(records))
    if output is not None:
        output.write_text(json.dumps({"works": records}, indent=2) + "\n", encoding="utf-8")
    return 0


def _patentsview_headers() -> dict[str, str]:
    """Optional PatentsView API key from the environment.

    Returns:
        Headers including X-Api-Key when set.
    """
    key = os.environ.get("PATENTSVIEW_API_KEY", "")
    if not key:
        return {}
    return {"X-Api-Key": key}
