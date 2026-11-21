"""Daedalus CLI: ingest the fixture slice or map HTTP JSON pages."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import httpx
from delphi_contracts.json_tree import namespace_dict

from daedalus.caps import CapsError, check_caps
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


def _text(raw: Mapping[str, object], key: str) -> str | None:
    """Return a non-empty string flag.

    Args:
        raw: Parsed CLI namespace.
        key: Flag name.

    Returns:
        The string, or None.
    """
    value = raw.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _flag(raw: Mapping[str, object], key: str) -> bool:
    """Return a store_true flag.

    Args:
        raw: Parsed CLI namespace.
        key: Flag name.

    Returns:
        True only when the flag was set.
    """
    return raw.get(key) is True


def _count(raw: Mapping[str, object], key: str, default: int) -> int:
    """Return an integer flag.

    Args:
        raw: Parsed CLI namespace.
        key: Flag name.
        default: Value when the flag is not an int.

    Returns:
        The integer flag.
    """
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _cli_path(raw: Mapping[str, object], key: str) -> Path | None:
    """Return a path flag.

    Args:
        raw: Parsed CLI namespace.
        key: Flag name.

    Returns:
        Path or None.
    """
    value = raw.get(key)
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


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
    parser.add_argument(
        "--live", action="store_true", help="Fetch SYS-009 OpenAlex pages"
    )
    parser.add_argument(
        "--live-patents",
        action="store_true",
        help=(
            "Fetch SYS-009 patents from EPO/WIPO/PatSnap/Lens when credentials are set"
        ),
    )
    parser.add_argument("--per-subcategory", type=int, default=25)
    parser.add_argument(
        "--mailto",
        default=os.environ.get("DELPHI_MAILTO", "delphi-engine@localhost"),
    )
    parser.add_argument("--output", type=Path, default=None)
    raw = namespace_dict(parser.parse_args(argv))
    subcategory = _text(raw, "subcategory") or "two_d_codes"
    mailto = _text(raw, "mailto") or "delphi-engine@localhost"
    per_subcategory = _count(raw, "per_subcategory", 25)
    output = _cli_path(raw, "output")
    openalex_url = _text(raw, "openalex_url")
    if openalex_url:
        with httpx.Client() as client:
            records = fetch_openalex(openalex_url, subcategory, client)
        return _emit(records, output)
    patentsview_url = _text(raw, "patentsview_url")
    if patentsview_url:
        headers = _header("X-Api-Key", os.environ.get("PATENTSVIEW_API_KEY", ""))
        with httpx.Client(headers=headers) as client:
            records = fetch_patentsview(patentsview_url, subcategory, client)
        return _emit(records, output)
    epo_url = _text(raw, "epo_url")
    if epo_url:
        headers = _epo_bearer_headers()
        with httpx.Client(headers=headers) as client:
            records = fetch_epo(epo_url, subcategory, client)
        return _emit(records, output)
    wipo_url = _text(raw, "wipo_url")
    if wipo_url:
        headers = _header("X-API-Key", os.environ.get("WIPO_API_KEY", ""))
        with httpx.Client(headers=headers) as client:
            records = fetch_wipo(wipo_url, subcategory, client)
        return _emit(records, output)
    patsnap_url = _text(raw, "patsnap_url")
    if patsnap_url:
        headers = _bearer(os.environ.get("PATSNAP_API_KEY", ""))
        with httpx.Client(headers=headers) as client:
            records = fetch_patsnap(patsnap_url, subcategory, client)
        return _emit(records, output)
    lens_url = _text(raw, "lens_url")
    if lens_url:
        headers = _bearer(os.environ.get("LENS_API_TOKEN", ""))
        with httpx.Client(headers=headers) as client:
            records = fetch_lens(lens_url, subcategory, client)
        return _emit(records, output)
    if _flag(raw, "live"):
        with httpx.Client(
            headers={"User-Agent": f"delphi-engine ({mailto})"}
        ) as client:
            records = fetch_named_slice(
                client,
                per_subcategory=per_subcategory,
                mailto=mailto,
            )
        return _emit(records, output)
    if _flag(raw, "live_patents"):
        with httpx.Client(
            headers={"User-Agent": f"delphi-engine ({mailto})"}
        ) as client:
            records = fetch_patent_slice(
                client,
                per_subcategory=per_subcategory,
                epo_key=os.environ.get("EPO_OPS_KEY", ""),
                epo_secret=os.environ.get("EPO_OPS_SECRET", ""),
                wipo_key=os.environ.get("WIPO_API_KEY", ""),
                wipo_url=os.environ.get("WIPO_PATENTSCOPE_URL") or WIPO_SEARCH_URL,
                patsnap_key=os.environ.get("PATSNAP_API_KEY", ""),
                lens_token=os.environ.get("LENS_API_TOKEN", ""),
            )
        return _emit(records, output)
    fixture = load_fixture(_cli_path(raw, "fixture"))
    print(len(fixture))
    if _flag(raw, "dry_run"):
        return 0
    return 0


def _emit(records: Sequence[Mapping[str, object]], output: Path | None) -> int:
    """Print count and optionally write works JSON.

    Args:
        records: Ingest dicts.
        output: Optional JSON path.

    Returns:
        Exit code.
    """
    counts: dict[str, int] = {}
    for record in records:
        subcategory = str(record.get("subcategory", ""))
        counts[subcategory] = counts.get(subcategory, 0) + 1
    try:
        check_caps(counts)
    except CapsError as exc:
        print(f"caps: {exc}")
        return 2
    print(len(records))
    if output is not None:
        output.write_text(
            json.dumps({"works": records}, indent=2) + "\n", encoding="utf-8"
        )
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
