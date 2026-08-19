"""HTTP page fetch for OpenAlex and PatentsView with retries."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid5

import httpx
from delphi_contracts.enums import SubcategoryId

from daedalus.caps import allowed_text

__all__ = [
    "FetchError",
    "OPENALEX_SEARCH",
    "fetch_named_slice",
    "fetch_openalex",
    "fetch_patentsview",
    "reconstruct_abstract",
]

_LOG = logging.getLogger("daedalus.fetch")
_OPENALEX_WORKS = "https://api.openalex.org/works"

OPENALEX_SEARCH: dict[str, str] = {
    SubcategoryId.TRANSFORMERS_FOUNDATION_MODELS.value: (
        'transformer OR "foundation model" OR "vision transformer"'
    ),
    SubcategoryId.COMPUTER_VISION.value: ('"document image" OR "camera capture" OR barcode OR QR'),
    SubcategoryId.STEGANOGRAPHY.value: (
        'steganography OR steganalysis OR watermarking OR "information hiding"'
    ),
    SubcategoryId.TWO_D_CODES.value: 'QR OR "data matrix" OR "2D barcode" OR Aztec OR PDF417',
}


class FetchError(RuntimeError):
    """Raised when an HTTP page cannot be fetched after retries."""


def reconstruct_abstract(index: object) -> str:
    """Rebuild OpenAlex inverted-index abstracts.

    Args:
        index: Word to position lists, or already-plain text.

    Returns:
        Concatenated abstract, or empty string.
    """
    if isinstance(index, str):
        return index
    if not isinstance(index, dict) or not index:
        return ""
    positions: dict[int, str] = {}
    for word, locs in index.items():
        if not isinstance(locs, list):
            continue
        for loc in locs:
            if isinstance(loc, int):
                positions[loc] = str(word)
    if not positions:
        return ""
    size = max(positions) + 1
    return " ".join(positions.get(offset, "") for offset in range(size)).strip()


def fetch_openalex(
    url: str,
    subcategory: str,
    client: httpx.Client,
    attempts: int = 3,
) -> list[dict[str, Any]]:
    """Fetch one OpenAlex works page and map ingest records.

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
    return _map_openalex_rows(rows, subcategory)


def fetch_patentsview(
    url: str,
    subcategory: str,
    client: httpx.Client,
    attempts: int = 3,
) -> list[dict[str, Any]]:
    """Fetch one PatentsView patents page and map ingest records.

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


def fetch_named_slice(
    client: httpx.Client,
    per_subcategory: int = 25,
    mailto: str = "delphi-engine@localhost",
    attempts: int = 3,
) -> list[dict[str, Any]]:
    """Page OpenAlex for all four SYS-009 subcategories.

    Args:
        client: Injected HTTP client.
        per_subcategory: Max works kept per subcategory after caps filters.
        mailto: OpenAlex polite-pool address.
        attempts: GET retries per page.

    Returns:
        Fixture-shaped records. Does not hit tens-of-thousands caps by default.
    """
    collected: list[dict[str, Any]] = []
    for subcategory, query in OPENALEX_SEARCH.items():
        collected.extend(
            _search_openalex(
                client,
                query,
                subcategory,
                per_subcategory,
                mailto,
                attempts,
            )
        )
    return collected


def _search_openalex(
    client: httpx.Client,
    query: str,
    subcategory: str,
    limit: int,
    mailto: str,
    attempts: int,
) -> list[dict[str, Any]]:
    """Cursor-page one OpenAlex search until limit.

    Args:
        client: HTTP client.
        query: OpenAlex search string.
        subcategory: SYS-009 id.
        limit: Max mapped records.
        mailto: Polite-pool address.
        attempts: Retries per page.

    Returns:
        Mapped records that pass allowed_text.
    """
    records: list[dict[str, Any]] = []
    cursor: str | None = "*"
    while cursor and len(records) < limit:
        remaining = min(50, limit - len(records))
        params = {
            "search": query,
            "per_page": remaining,
            "filter": "is_paratext:false",
            "cursor": cursor,
            "mailto": mailto,
        }
        url = f"{_OPENALEX_WORKS}?{urlencode(params)}"
        payload = _get_json(url, client, attempts)
        if not isinstance(payload, dict):
            break
        results = payload.get("results", [])
        rows = results if isinstance(results, list) else []
        for item in _map_openalex_rows(rows, subcategory):
            blob = f"{item.get('title', '')} {item.get('abstract', '')}"
            if allowed_text(blob, subcategory):
                records.append(item)
            if len(records) >= limit:
                break
        raw_meta = payload.get("meta")
        meta = raw_meta if isinstance(raw_meta, dict) else {}
        nxt = meta.get("next_cursor")
        cursor = str(nxt) if nxt else None
    return records[:limit]


def _map_openalex_rows(rows: list[object], subcategory: str) -> list[dict[str, Any]]:
    """Map OpenAlex JSON rows, skipping poison.

    Args:
        rows: Result objects.
        subcategory: SYS-009 id.

    Returns:
        Ingest records.
    """
    records: list[dict[str, Any]] = []
    for item in rows:
        try:
            records.append(_openalex_record(item, subcategory))
        except (KeyError, TypeError, ValueError) as exc:
            _LOG.warning("skipping poison OpenAlex row: %s", exc)
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
    """Map one OpenAlex work (live API or simplified fixture shape).

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
    title = str(item.get("title") or item.get("display_name") or "")
    if not title:
        raise KeyError("title")
    published = _publication_date(item)
    doi_value = _doi_value(item.get("doi"))
    abstract = str(item.get("abstract") or "") or reconstruct_abstract(
        item.get("abstract_inverted_index")
    )
    cites = [
        str(uuid5(NAMESPACE_URL, str(ref))) for ref in item.get("referenced_works") or () if ref
    ]
    record: dict[str, Any] = {
        "id": work_id,
        "kind": "paper",
        "title": title,
        "abstract": abstract,
        "published_on": published,
        "openalex": openalex_id,
        "authors": _string_names(item, "authors") or _authorship_names(item),
        "keywords": _string_names(item, "keywords") or _display_names(item.get("concepts")),
        "subcategory": subcategory,
        "cites": cites,
    }
    if doi_value:
        record["doi"] = doi_value
    arxiv = _nested_id(item, "arxiv")
    if arxiv:
        record["arxiv"] = arxiv
    return record


def _patentsview_record(item: object, subcategory: str) -> dict[str, Any]:
    """Map one PatentsView patent (live or simplified shape).

    Args:
        item: JSON object.
        subcategory: SYS-009 id.

    Returns:
        Fixture-shaped record.
    """
    if not isinstance(item, dict):
        raise TypeError("patentsview row must be an object")
    patent_id = str(item.get("patent_id") or item.get("patent_number") or "")
    if not patent_id:
        raise KeyError("patent_id")
    work_id = str(uuid5(NAMESPACE_URL, patent_id))
    title = str(item.get("patent_title") or item.get("title") or "")
    if not title:
        raise KeyError("title")
    published = str(
        item.get("patent_date") or item.get("publication_date") or item.get("published_on") or ""
    )
    if not published:
        raise KeyError("publication_date")
    return {
        "id": work_id,
        "kind": "patent",
        "title": title,
        "abstract": str(item.get("patent_abstract") or item.get("abstract") or ""),
        "published_on": published,
        "patent": patent_id,
        "authors": _string_names(item, "authors") or _inventor_names(item),
        "keywords": _string_names(item, "keywords") or _cpc_codes(item),
        "subcategory": subcategory,
        "cites": [],
    }


def _publication_date(item: dict[str, Any]) -> str:
    """Return an ISO date string.

    Args:
        item: OpenAlex work.

    Returns:
        YYYY-MM-DD.

    Raises:
        KeyError: When no date is present.
    """
    published = item.get("publication_date")
    if published:
        return str(published)
    year = item.get("publication_year")
    if year:
        return f"{int(year)}-01-01"
    raise KeyError("publication_date")


def _doi_value(doi: object) -> str | None:
    """Strip a DOI URL prefix.

    Args:
        doi: Raw DOI field.

    Returns:
        Bare DOI or None.
    """
    if not doi:
        return None
    return str(doi).removeprefix("https://doi.org/")


def _string_names(item: dict[str, Any], key: str) -> list[str]:
    """Return a list of strings stored under key.

    Args:
        item: Source object.
        key: Field name.

    Returns:
        Names when the field is already a list of strings.
    """
    raw = item.get(key)
    if isinstance(raw, list) and raw and all(isinstance(value, str) for value in raw):
        return [str(value) for value in raw]
    if isinstance(raw, list):
        names = _display_names(raw)
        if names:
            return names
    return []


def _display_names(rows: object) -> list[str]:
    """Collect display_name from object rows.

    Args:
        rows: List of dicts.

    Returns:
        Display names.
    """
    names: list[str] = []
    if not isinstance(rows, list):
        return names
    for row in rows:
        if isinstance(row, dict) and row.get("display_name"):
            names.append(str(row["display_name"]))
    return names


def _authorship_names(item: dict[str, Any]) -> list[str]:
    """Authors from OpenAlex authorships.

    Args:
        item: OpenAlex work.

    Returns:
        Author display names.
    """
    names: list[str] = []
    for row in item.get("authorships") or ():
        if not isinstance(row, dict):
            continue
        author = row.get("author") if isinstance(row.get("author"), dict) else {}
        name = (author or {}).get("display_name") or row.get("raw_author_name")
        if name:
            names.append(str(name))
    return names


def _inventor_names(item: dict[str, Any]) -> list[str]:
    """Inventors from PatentsView nested objects.

    Args:
        item: Patent object.

    Returns:
        Inventor names.
    """
    names: list[str] = []
    for row in item.get("inventors") or ():
        if isinstance(row, str):
            names.append(row)
            continue
        if not isinstance(row, dict):
            continue
        first = str(row.get("inventor_first_name") or row.get("first_name") or "")
        last = str(row.get("inventor_last_name") or row.get("last_name") or "")
        name = f"{first} {last}".strip()
        if name:
            names.append(name)
    return names


def _cpc_codes(item: dict[str, Any]) -> list[str]:
    """CPC class symbols when present.

    Args:
        item: Patent object.

    Returns:
        CPC codes.
    """
    codes: list[str] = []
    for row in item.get("cpc_current") or item.get("cpcs") or ():
        if isinstance(row, str):
            codes.append(row)
        elif isinstance(row, dict):
            code = row.get("cpc_subclass_id") or row.get("symbol") or row.get("cpc_class_id")
            if code:
                codes.append(str(code))
    return codes


def _nested_id(item: dict[str, Any], key: str) -> str | None:
    """Read ids.<key> when present.

    Args:
        item: OpenAlex work.
        key: ids object key.

    Returns:
        Identifier or None.
    """
    ids = item.get("ids")
    if isinstance(ids, dict) and ids.get(key):
        return str(ids[key])
    return None
