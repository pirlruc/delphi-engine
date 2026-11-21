"""HTTP page fetch for OpenAlex and PatentsView with retries."""

from __future__ import annotations

import logging
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid5

import httpx
from delphi_contracts.enums import SubcategoryId
from delphi_contracts.identity import normalize_doi, normalize_patent
from delphi_contracts.json_tree import as_list, is_object_dict, is_object_list

from daedalus.caps import allowed_text
from daedalus.ingest import IngestRecord
from daedalus.retry import request_json

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
    SubcategoryId.COMPUTER_VISION.value: (
        '"document image" OR "camera capture" OR barcode OR QR'
    ),
    SubcategoryId.STEGANOGRAPHY.value: (
        'steganography OR steganalysis OR watermarking OR "information hiding"'
    ),
    SubcategoryId.TWO_D_CODES.value: (
        'QR OR "data matrix" OR "2D barcode" OR Aztec OR PDF417'
    ),
}


class FetchError(RuntimeError):
    """Raised when an HTTP page cannot be fetched after retries."""


_MAX_ABSTRACT_POSITIONS = 20_000


def reconstruct_abstract(index: object) -> str:
    """Rebuild OpenAlex inverted-index abstracts.

    Args:
        index: Word to position lists, or already-plain text.

    Returns:
        Concatenated abstract, or empty string.
    """
    if isinstance(index, str):
        return index
    if not is_object_dict(index) or not index:
        return ""
    positions: dict[int, str] = {}
    for word, locs in index.items():
        if not is_object_list(locs):
            continue
        for loc in locs:
            if isinstance(loc, int):
                positions[loc] = str(word)
    if not positions:
        return ""
    capped = {
        loc: word
        for loc, word in positions.items()
        if 0 <= loc < _MAX_ABSTRACT_POSITIONS
    }
    if not capped:
        return ""
    size = max(capped) + 1
    return " ".join(capped.get(offset, "") for offset in range(size)).strip()


def fetch_openalex(
    url: str,
    subcategory: str,
    client: httpx.Client,
    attempts: int = 3,
) -> list[IngestRecord]:
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
    results = payload.get("results", []) if is_object_dict(payload) else []
    rows = results if is_object_list(results) else []
    return _map_openalex_rows(rows, subcategory)


def fetch_patentsview(
    url: str,
    subcategory: str,
    client: httpx.Client,
    attempts: int = 3,
) -> list[IngestRecord]:
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
    patents = payload.get("patents", []) if is_object_dict(payload) else []
    rows = patents if is_object_list(patents) else []
    records: list[IngestRecord] = []
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
) -> list[IngestRecord]:
    """Page OpenAlex for all four SYS-009 subcategories.

    Args:
        client: Injected HTTP client.
        per_subcategory: Max works kept per subcategory after caps filters.
        mailto: OpenAlex polite-pool address.
        attempts: GET retries per page.

    Returns:
        Fixture-shaped records. Does not hit tens-of-thousands caps by default.
    """
    collected: list[IngestRecord] = []
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
) -> list[IngestRecord]:
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
    records: list[IngestRecord] = []
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
        if not is_object_dict(payload):
            break
        results = payload.get("results", [])
        rows = results if is_object_list(results) else []
        for item in _map_openalex_rows(rows, subcategory):
            blob = f"{item.get('title', '')} {item.get('abstract', '')}"
            if allowed_text(blob, subcategory):
                records.append(item)
            if len(records) >= limit:
                break
        raw_meta = payload.get("meta")
        meta = raw_meta if is_object_dict(raw_meta) else {}
        nxt = meta.get("next_cursor")
        cursor = str(nxt) if nxt else None
    return records[:limit]


def _map_openalex_rows(rows: list[object], subcategory: str) -> list[IngestRecord]:
    """Map OpenAlex JSON rows, skipping poison.

    Args:
        rows: Result objects.
        subcategory: SYS-009 id.

    Returns:
        Ingest records.
    """
    records: list[IngestRecord] = []
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
    try:
        return request_json(client, "GET", url, attempts=attempts)
    except (httpx.HTTPError, ValueError) as exc:
        raise FetchError(f"fetch failed after retries: {url}") from exc


def _openalex_record(item: object, subcategory: str) -> IngestRecord:
    """Map one OpenAlex work (live API or simplified fixture shape).

    Args:
        item: JSON object.
        subcategory: SYS-009 id.

    Returns:
        Fixture-shaped record.
    """
    if not is_object_dict(item):
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
        str(uuid5(NAMESPACE_URL, str(ref)))
        for ref in as_list(item.get("referenced_works"))
        if ref
    ]
    record: IngestRecord = {
        "id": work_id,
        "kind": "paper",
        "title": title,
        "abstract": abstract,
        "published_on": published,
        "openalex": openalex_id,
        "authors": _string_names(item, "authors") or _authorship_names(item),
        "keywords": _string_names(item, "keywords")
        or _display_names(item.get("concepts")),
        "subcategory": subcategory,
        "cites": cites,
    }
    if doi_value:
        record["doi"] = doi_value
    arxiv = _nested_id(item, "arxiv")
    if arxiv:
        record["arxiv"] = arxiv
    return record


def _patentsview_record(item: object, subcategory: str) -> IngestRecord:
    """Map one PatentsView patent (live or simplified shape).

    Args:
        item: JSON object.
        subcategory: SYS-009 id.

    Returns:
        Fixture-shaped record.
    """
    if not is_object_dict(item):
        raise TypeError("patentsview row must be an object")
    patent_id = str(item.get("patent_id") or item.get("patent_number") or "")
    if not patent_id:
        raise KeyError("patent_id")
    normalized = normalize_patent(patent_id)
    work_id = str(uuid5(NAMESPACE_URL, normalized))
    title = str(item.get("patent_title") or item.get("title") or "")
    if not title:
        raise KeyError("title")
    published = str(
        item.get("patent_date")
        or item.get("publication_date")
        or item.get("published_on")
        or ""
    )
    if not published:
        raise KeyError("publication_date")
    claims_raw = (
        item.get("claims") or item.get("claim_text") or item.get("independent_claims")
    )
    claims: list[str] = []
    if is_object_list(claims_raw):
        for row in claims_raw:
            if isinstance(row, str) and row.strip():
                claims.append(row.strip())
            elif is_object_dict(row):
                text = str(row.get("claim_text") or row.get("text") or "").strip()
                if text:
                    claims.append(text)
    elif isinstance(claims_raw, str) and claims_raw.strip():
        claims = [claims_raw.strip()]
    return {
        "id": work_id,
        "kind": "patent",
        "title": title,
        "abstract": str(item.get("patent_abstract") or item.get("abstract") or ""),
        "published_on": published,
        "patent": normalized,
        "authors": _string_names(item, "authors") or _inventor_names(item),
        "keywords": _string_names(item, "keywords") or _cpc_codes(item),
        "claims": claims,
        "subcategory": subcategory,
        "cites": [],
    }


def _publication_date(item: dict[str, object]) -> str:
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
    if isinstance(year, int) and not isinstance(year, bool):
        return f"{year}-01-01"
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
    return normalize_doi(str(doi)) or None


def _string_names(item: dict[str, object], key: str) -> list[str]:
    """Return a list of strings stored under key.

    Args:
        item: Source object.
        key: Field name.

    Returns:
        Names when the field is already a list of strings.
    """
    raw = item.get(key)
    if is_object_list(raw) and raw and all(isinstance(value, str) for value in raw):
        return [str(value) for value in raw]
    if is_object_list(raw):
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
    if not is_object_list(rows):
        return names
    for row in rows:
        if is_object_dict(row) and row.get("display_name"):
            names.append(str(row["display_name"]))
    return names


def _authorship_names(item: dict[str, object]) -> list[str]:
    """Authors from OpenAlex authorships.

    Args:
        item: OpenAlex work.

    Returns:
        Author display names.
    """
    names: list[str] = []
    for row in as_list(item.get("authorships")):
        if not is_object_dict(row):
            continue
        author_raw = row.get("author")
        author = author_raw if is_object_dict(author_raw) else {}
        name = author.get("display_name") or row.get("raw_author_name")
        if name:
            names.append(str(name))
    return names


def _inventor_names(item: dict[str, object]) -> list[str]:
    """Inventors from PatentsView nested objects.

    Args:
        item: Patent object.

    Returns:
        Inventor names.
    """
    names: list[str] = []
    for row in as_list(item.get("inventors")):
        if isinstance(row, str):
            names.append(row)
            continue
        if not is_object_dict(row):
            continue
        first = str(row.get("inventor_first_name") or row.get("first_name") or "")
        last = str(row.get("inventor_last_name") or row.get("last_name") or "")
        name = f"{first} {last}".strip()
        if name:
            names.append(name)
    return names


def _cpc_codes(item: dict[str, object]) -> list[str]:
    """CPC class symbols when present.

    Args:
        item: Patent object.

    Returns:
        CPC codes.
    """
    codes: list[str] = []
    for row in as_list(item.get("cpc_current") or item.get("cpcs")):
        if isinstance(row, str):
            codes.append(row)
        elif is_object_dict(row):
            code = (
                row.get("cpc_subclass_id")
                or row.get("symbol")
                or row.get("cpc_class_id")
            )
            if code:
                codes.append(str(code))
    return codes


def _nested_id(item: dict[str, object], key: str) -> str | None:
    """Read ids.<key> when present.

    Args:
        item: OpenAlex work.
        key: ids object key.

    Returns:
        Identifier or None.
    """
    ids = item.get("ids")
    if is_object_dict(ids) and ids.get(key):
        return str(ids[key])
    return None
