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
from daedalus.patents import (
    WIPO_SEARCH_URL,
    epo_access_token,
    fetch_epo,
    fetch_lens,
    fetch_patent_slice,
    fetch_patsnap,
    fetch_wipo,
)

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
    parser.add_argument("--epo-url", default=None)
    parser.add_argument("--wipo-url", default=None)
    parser.add_argument("--patsnap-url", default=None)
    parser.add_argument("--lens-url", default=None)
    parser.add_argument("--subcategory", default="two_d_codes")
    parser.add_argument("--live", action="store_true", help="Fetch SYS-009 OpenAlex pages")
    parser.add_argument(
        "--live-patents",
        action="store_true",
        help="Fetch SYS-009 patents from EPO/WIPO/PatSnap/Lens when credentials are set",
    )
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
        headers = _header("X-Api-Key", os.environ.get("PATENTSVIEW_API_KEY", ""))
        with httpx.Client(headers=headers) as client:
            records = fetch_patentsview(args.patentsview_url, args.subcategory, client)
        return _emit(records, args.output)
    if args.epo_url:
        headers = _epo_bearer_headers()
        with httpx.Client(headers=headers) as client:
            records = fetch_epo(args.epo_url, args.subcategory, client)
        return _emit(records, args.output)
    if args.wipo_url:
        headers = _header("X-API-Key", os.environ.get("WIPO_API_KEY", ""))
        with httpx.Client(headers=headers) as client:
            records = fetch_wipo(args.wipo_url, args.subcategory, client)
        return _emit(records, args.output)
    if args.patsnap_url:
        headers = _bearer(os.environ.get("PATSNAP_API_KEY", ""))
        with httpx.Client(headers=headers) as client:
            records = fetch_patsnap(args.patsnap_url, args.subcategory, client)
        return _emit(records, args.output)
    if args.lens_url:
        headers = _bearer(os.environ.get("LENS_API_TOKEN", ""))
        with httpx.Client(headers=headers) as client:
            records = fetch_lens(args.lens_url, args.subcategory, client)
        return _emit(records, args.output)
    if args.live:
        with httpx.Client(headers={"User-Agent": f"delphi-engine ({args.mailto})"}) as client:
            records = fetch_named_slice(
                client,
                per_subcategory=args.per_subcategory,
                mailto=args.mailto,
            )
        return _emit(records, args.output)
    if args.live_patents:
        with httpx.Client(headers={"User-Agent": f"delphi-engine ({args.mailto})"}) as client:
            records = fetch_patent_slice(
                client,
                per_subcategory=args.per_subcategory,
                epo_key=os.environ.get("EPO_OPS_KEY", ""),
                epo_secret=os.environ.get("EPO_OPS_SECRET", ""),
                wipo_key=os.environ.get("WIPO_API_KEY", ""),
                wipo_url=os.environ.get("WIPO_PATENTSCOPE_URL") or WIPO_SEARCH_URL,
                patsnap_key=os.environ.get("PATSNAP_API_KEY", ""),
                lens_token=os.environ.get("LENS_API_TOKEN", ""),
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


def _header(name: str, value: str) -> dict[str, str]:
    """Build a single optional header.

    Args:
        name: Header name.
        value: Header value; omitted when empty.

    Returns:
        Headers dict.
    """
    if not value:
        return {}
    return {name: value}


def _bearer(token: str) -> dict[str, str]:
    """Authorization Bearer header when a token is set.

    Args:
        token: API token.

    Returns:
        Headers dict.
    """
    return _header("Authorization", f"Bearer {token}" if token else "")


def _epo_bearer_headers() -> dict[str, str]:
    """OPS Bearer token from EPO_OPS_KEY/SECRET, or empty.

    Returns:
        Authorization header when credentials work.
    """
    key = os.environ.get("EPO_OPS_KEY", "")
    secret = os.environ.get("EPO_OPS_SECRET", "")
    if not key or not secret:
        return {}
    with httpx.Client() as client:
        token = epo_access_token(client, key, secret)
    return {"Authorization": f"Bearer {token}"}
