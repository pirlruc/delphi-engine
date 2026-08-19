"""HTTP page fetch for OpenAlex and PatentsView with retries."""

from __future__ import annotations

import logging
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx

__all__ = ["FetchError", "fetch_openalex", "fetch_patentsview"]

_LOG = logging.getLogger("daedalus.fetch")


class FetchError(RuntimeError):
    """Raised when an HTTP page cannot be fetched after retries."""


def fetch_openalex(
    url: str,
    subcategory: str,
    client: httpx.Client,
    attempts: int = 3,
) -> list[dict[str, Any]]:
    """Fetch one OpenAlex works page and map fixture-shaped records.

    Args:
        url: Fully qualified OpenAlex works URL.
        subcategory: SYS-009 id applied to every row.
        client: Injected HTTP client.
        attempts: GET retries on HTTP errors.

    Returns:
        Records ready for ingest_records. Poison rows are skipped.
    """
    payload = _get_json(url, client, attempts)
    results = payload.get("results", []) if isinstance(payload, dict) else []
    rows = results if isinstance(results, list) else []
    records: list[dict[str, Any]] = []
    for item in rows:
        try:
            records.append(_openalex_record(item, subcategory))
        except (KeyError, TypeError, ValueError) as exc:
            _LOG.warning("skipping poison OpenAlex row: %s", exc)
    return records


def fetch_patentsview(
    url: str,
    subcategory: str,
    client: httpx.Client,
    attempts: int = 3,
) -> list[dict[str, Any]]:
    """Fetch one PatentsView patents page and map fixture-shaped records.

    Args:
        url: Fully qualified PatentsView URL.
        subcategory: SYS-009 id applied to every row.
        client: Injected HTTP client.
        attempts: GET retries on HTTP errors.

    Returns:
        Records ready for ingest_records. Poison rows are skipped.
    """
    payload = _get_json(url, client, attempts)
    patents = payload.get("patents", []) if isinstance(payload, dict) else []
    rows = patents if isinstance(patents, list) else []
    records: list[dict[str, Any]] = []
    for item in rows:
        try:
            records.append(_patentsview_record(item, subcategory))
        except (KeyError, TypeError, ValueError) as exc:
            _LOG.warning("skipping poison PatentsView row: %s", exc)
    return records


def _get_json(url: str, client: httpx.Client, attempts: int) -> object:
    """GET JSON with retries.

    Args:
        url: Request URL.
        client: HTTP client.
        attempts: Retry count.

    Returns:
        Parsed JSON.

    """
    last: Exception | None = None
    for _attempt in range(max(attempts, 1)):
        try:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
    raise FetchError(f"fetch failed after retries: {url}") from last


def _openalex_record(item: object, subcategory: str) -> dict[str, Any]:
    """Map one OpenAlex work.

    Args:
        item: JSON object.
        subcategory: SYS-009 id.

    Returns:
        Fixture-shaped record.
    """
    if not isinstance(item, dict):
        raise TypeError("openalex row must be an object")
    openalex_id = str(item["id"])
    work_id = str(uuid5(NAMESPACE_URL, openalex_id))
    doi = item.get("doi")
    doi_value = str(doi).removeprefix("https://doi.org/") if doi else None
    published = item.get("publication_date")
    if not published:
        raise KeyError("publication_date")
    return {
        "id": work_id,
        "kind": "paper",
        "title": str(item["title"]),
        "abstract": str(item.get("abstract") or ""),
        "published_on": str(published),
        "doi": doi_value,
        "openalex": openalex_id,
        "authors": [str(name) for name in item.get("authors", ())],
        "keywords": [str(name) for name in item.get("keywords", ())],
        "subcategory": subcategory,
        "cites": [],
    }


def _patentsview_record(item: object, subcategory: str) -> dict[str, Any]:
    """Map one PatentsView patent.

    Args:
        item: JSON object.
        subcategory: SYS-009 id.

    Returns:
        Fixture-shaped record.
    """
    if not isinstance(item, dict):
        raise TypeError("patentsview row must be an object")
    patent_id = str(item.get("patent_id") or item["patent_number"])
    work_id = str(uuid5(NAMESPACE_URL, patent_id))
    return {
        "id": work_id,
        "kind": "patent",
        "title": str(item.get("patent_title") or item["title"]),
        "abstract": str(item.get("patent_abstract") or item.get("abstract") or ""),
        "published_on": str(item.get("patent_date") or item["publication_date"]),
        "patent": patent_id,
        "authors": [str(name) for name in item.get("authors", ())],
        "keywords": [str(name) for name in item.get("keywords", ())],
        "subcategory": subcategory,
        "cites": [],
    }
