"""Patent-office HTTP fetchers: EPO OPS, WIPO, PatSnap, and Lens.org."""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid5

import httpx
from delphi_contracts.enums import SubcategoryId
from delphi_contracts.identity import normalize_patent
from delphi_contracts.json_tree import is_object_dict, is_object_list, parse_json

from daedalus.caps import allowed_text
from daedalus.fetch import FetchError
from daedalus.ingest import IngestRecord
from daedalus.net import assert_allowed_url
from daedalus.retry import header_text, request_json

__all__ = [
    "PATENT_SEARCH",
    "WIPO_SEARCH_URL",
    "epo_access_token",
    "fetch_epo",
    "fetch_lens",
    "fetch_patent_slice",
    "fetch_patsnap",
    "fetch_wipo",
    "search_epo",
    "search_lens",
    "search_patsnap",
    "search_wipo",
]

_LOG = logging.getLogger("daedalus.patents")
_EPO_TOKEN = "https://ops.epo.org/3.2/auth/accesstoken"  # nosec B105
_EPO_SEARCH = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"
_LENS_SEARCH = "https://api.lens.org/patent/search"
_PATSNAP_SEARCH = "https://connect.patsnap.com/search/patent/query-search-patent/v2"
_WIPO_SEARCH = "https://patentscope.wipo.int/search/rest/patents"
WIPO_SEARCH_URL = _WIPO_SEARCH

PATENT_SEARCH: dict[str, str] = {
    SubcategoryId.TRANSFORMERS_FOUNDATION_MODELS.value: (
        'transformer OR "foundation model" OR "vision transformer"'
    ),
    SubcategoryId.COMPUTER_VISION.value: (
        '"document image" OR "machine readable" OR barcode OR QR'
    ),
    SubcategoryId.STEGANOGRAPHY.value: (
        'steganography OR steganalysis OR watermarking OR "information hiding"'
    ),
    SubcategoryId.TWO_D_CODES.value: (
        'QR OR "data matrix" OR barcode OR Aztec OR PDF417'
    ),
}


def epo_access_token(
    client: httpx.Client, key: str, secret: str, attempts: int = 3
) -> str:
    """Request an OPS OAuth2 client-credentials token.

    Args:
        client: HTTP client.
        key: Consumer key from developers.epo.org.
        secret: Consumer secret.
        attempts: POST retries.

    Returns:
        Bearer access token.

    Raises:
        FetchError: When the token endpoint fails.
    """
    raw = base64.b64encode(f"{key}:{secret}".encode()).decode("ascii")
    headers = {
        "Authorization": f"Basic {raw}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = "grant_type=client_credentials"
    last: Exception | None = None
    for _attempt in range(max(attempts, 1)):
        try:
            response = client.post(
                _EPO_TOKEN, content=data, headers=headers, timeout=30.0
            )
            response.raise_for_status()
            payload = parse_json(response.content)
            token = payload.get("access_token") if is_object_dict(payload) else None
            if token:
                return str(token)
            raise FetchError("EPO token response missing access_token")
        except (httpx.HTTPError, ValueError, FetchError) as exc:
            last = exc
    raise FetchError("EPO token request failed after retries") from last


def fetch_epo(
    url: str,
    subcategory: str,
    client: httpx.Client,
    attempts: int = 3,
) -> list[IngestRecord]:
    """GET one EPO OPS JSON page and map ingest records.

    Args:
        url: Fully qualified OPS URL.
        subcategory: SYS-009 id.
        client: Injected HTTP client (Bearer token already set when live).
        attempts: GET retries.

    Returns:
        Fixture-shaped patent records. Poison rows are skipped.
    """
    payload = _get_json(url, client, attempts)
    return _map_rows(_epo_items(payload), subcategory, _epo_record)


def search_epo(
    query: str,
    subcategory: str,
    client: httpx.Client,
    limit: int = 25,
    attempts: int = 3,
) -> list[IngestRecord]:
    """CQL search OPS published-data biblio.

    Args:
        query: Keyword query; wrapped as ``ta=(...)``.
        subcategory: SYS-009 id.
        client: Authenticated HTTP client.
        limit: Max records (OPS Range 1-N).
        attempts: Retries.

    Returns:
        Mapped patent records.
    """
    params = {"q": f"ta=({query})", "Range": f"1-{max(1, min(limit, 100))}"}
    url = f"{_EPO_SEARCH}?{urlencode(params)}"
    return fetch_epo(url, subcategory, client, attempts=attempts)


def fetch_wipo(
    url: str,
    subcategory: str,
    client: httpx.Client,
    attempts: int = 3,
) -> list[IngestRecord]:
    """GET one WIPO PATENTSCOPE JSON page.

    Official PATENTSCOPE search is a paid SOAP/Java service. This client
    talks to a REST JSON gateway (set ``WIPO_PATENTSCOPE_URL``).

    Args:
        url: Fully qualified JSON URL.
        subcategory: SYS-009 id.
        client: HTTP client with X-API-Key when required.
        attempts: GET retries.

    Returns:
        Fixture-shaped patent records.
    """
    payload = _get_json(url, client, attempts)
    return _map_rows(_wipo_items(payload), subcategory, _wipo_record)


def search_wipo(
    query: str,
    subcategory: str,
    client: httpx.Client,
    base_url: str = _WIPO_SEARCH,
    limit: int = 25,
    attempts: int = 3,
) -> list[IngestRecord]:
    """Search a WIPO JSON gateway.

    Args:
        query: Keyword query.
        subcategory: SYS-009 id.
        client: HTTP client.
        base_url: REST search URL.
        limit: Page size hint.
        attempts: Retries.

    Returns:
        Mapped patent records.
    """
    params = {"q": query, "rows": str(limit)}
    url = f"{base_url.rstrip('/')}?{urlencode(params)}"
    return fetch_wipo(url, subcategory, client, attempts=attempts)


def fetch_patsnap(
    url: str,
    subcategory: str,
    client: httpx.Client,
    body: dict[str, object] | None = None,
    attempts: int = 3,
) -> list[IngestRecord]:
    """POST or GET one PatSnap patent-search page.

    Args:
        url: Fully qualified PatSnap URL.
        subcategory: SYS-009 id.
        client: HTTP client with Bearer API key.
        body: JSON body for POST search. GET when None.
        attempts: Retries.

    Returns:
        Fixture-shaped patent records.
    """
    if body is not None:
        payload = _post_json(url, client, body, attempts)
    else:
        payload = _get_json(url, client, attempts)
    return _map_rows(_patsnap_items(payload), subcategory, _patsnap_record)


def search_patsnap(
    query: str,
    subcategory: str,
    client: httpx.Client,
    limit: int = 25,
    attempts: int = 3,
) -> list[IngestRecord]:
    """PatSnap P002 analytics query search.

    Args:
        query: TACD keyword query.
        subcategory: SYS-009 id.
        client: Authenticated HTTP client.
        limit: Max rows (API cap 1000).
        attempts: Retries.

    Returns:
        Mapped patent records.
    """
    body = {"query_text": f"TACD: {query}", "limit": min(limit, 1000), "offset": 0}
    return fetch_patsnap(
        _PATSNAP_SEARCH, subcategory, client, body=body, attempts=attempts
    )


def fetch_lens(
    url: str,
    subcategory: str,
    client: httpx.Client,
    body: dict[str, object] | None = None,
    attempts: int = 3,
) -> list[IngestRecord]:
    """POST or GET one Lens.org patent-search page.

    Args:
        url: Fully qualified Lens URL.
        subcategory: SYS-009 id.
        client: HTTP client with Bearer token.
        body: JSON body for POST search. GET when None.
        attempts: Retries.

    Returns:
        Fixture-shaped patent records.
    """
    if body is not None:
        payload = _post_json(url, client, body, attempts)
    else:
        payload = _get_json(url, client, attempts)
    return _map_rows(_lens_items(payload), subcategory, _lens_record)


def search_lens(
    query: str,
    subcategory: str,
    client: httpx.Client,
    limit: int = 25,
    attempts: int = 3,
) -> list[IngestRecord]:
    """Lens patent search using a query_string over title and abstract.

    Args:
        query: Keyword query.
        subcategory: SYS-009 id.
        client: Authenticated HTTP client.
        limit: Page size.
        attempts: Retries.

    Returns:
        Mapped patent records.
    """
    body = {
        "query": {
            "query_string": {"query": query, "fields": ["title", "abstract", "claims"]}
        },
        "size": min(limit, 100),
        "include": [
            "biblio",
            "claims",
            "date_published",
            "jurisdiction",
            "doc_number",
            "lens_id",
        ],
    }
    return fetch_lens(_LENS_SEARCH, subcategory, client, body=body, attempts=attempts)


def fetch_patent_slice(
    client: httpx.Client,
    per_subcategory: int = 25,
    epo_key: str = "",
    epo_secret: str = "",  # nosec B107
    wipo_key: str = "",
    wipo_url: str = _WIPO_SEARCH,
    patsnap_key: str = "",
    lens_token: str = "",
    attempts: int = 3,
) -> list[IngestRecord]:
    """Page configured patent APIs for all four SYS-009 subcategories.

    Sources without credentials are skipped. Records are filtered by
    ``allowed_text`` and capped per subcategory across sources.

    Args:
        client: Shared HTTP client.
        per_subcategory: Max kept works per subcategory.
        epo_key: OPS consumer key.
        epo_secret: OPS consumer secret.
        wipo_key: PATENTSCOPE JSON gateway key.
        wipo_url: WIPO REST base URL.
        patsnap_key: PatSnap Bearer key (``sk-...``).
        lens_token: Lens.org API token.
        attempts: Retries per request.

    Returns:
        Combined ingest records.

    Raises:
        UrlNotAllowed: The WIPO URL is not https on an allowed host.
    """
    if wipo_key:
        assert_allowed_url(wipo_url)
    collected: list[IngestRecord] = []
    epo_token = ""  # nosec B105
    if epo_key and epo_secret:
        epo_token = epo_access_token(client, epo_key, epo_secret, attempts=attempts)
    for subcategory, query in PATENT_SEARCH.items():
        bucket: list[IngestRecord] = []
        if epo_token:
            with _header_scope(client, "Authorization", f"Bearer {epo_token}"):
                bucket.extend(
                    search_epo(
                        query,
                        subcategory,
                        client,
                        limit=per_subcategory,
                        attempts=attempts,
                    )
                )
        if wipo_key:
            with _header_scope(client, "X-API-Key", wipo_key):
                bucket.extend(
                    search_wipo(
                        query,
                        subcategory,
                        client,
                        base_url=wipo_url,
                        limit=per_subcategory,
                        attempts=attempts,
                    )
                )
        if patsnap_key:
            with _header_scope(client, "Authorization", f"Bearer {patsnap_key}"):
                bucket.extend(
                    search_patsnap(
                        query,
                        subcategory,
                        client,
                        limit=per_subcategory,
                        attempts=attempts,
                    )
                )
        if lens_token:
            with _header_scope(client, "Authorization", f"Bearer {lens_token}"):
                bucket.extend(
                    search_lens(
                        query,
                        subcategory,
                        client,
                        limit=per_subcategory,
                        attempts=attempts,
                    )
                )
        kept = 0
        seen: set[str] = set()
        for item in bucket:
            patent = str(item.get("patent", ""))
            if patent in seen:
                continue
            blob = f"{item.get('title', '')} {item.get('abstract', '')}"
            if not allowed_text(blob, subcategory):
                continue
            seen.add(patent)
            collected.append(item)
            kept += 1
            if kept >= per_subcategory:
                break
    return collected


@contextmanager
def _header_scope(client: httpx.Client, name: str, value: str) -> Iterator[None]:
    """Temporarily set one HTTP header on the client.

    Args:
        client: Shared HTTP client.
        name: Header name.
        value: Header value.

    Yields:
        None.
    """
    previous = header_text(client.headers, name)
    client.headers[name] = value
    try:
        yield
    finally:
        if previous is None:
            client.headers.pop(name, None)
        else:
            client.headers[name] = previous


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
        return request_json(
            client,
            "GET",
            url,
            attempts=attempts,
            headers={"Accept": "application/json"},
        )
    except (httpx.HTTPError, ValueError) as exc:
        raise FetchError(f"fetch failed after retries: {url}") from exc


def _post_json(
    url: str,
    client: httpx.Client,
    body: dict[str, object],
    attempts: int,
) -> object:
    """POST JSON with retries.

    Args:
        url: Request URL.
        client: HTTP client.
        body: JSON object.
        attempts: Retry count.

    Returns:
        Parsed JSON.
    """
    try:
        return request_json(
            client,
            "POST",
            url,
            attempts=attempts,
            json_body=body,
            headers={"Accept": "application/json"},
        )
    except (httpx.HTTPError, ValueError) as exc:
        raise FetchError(f"post failed after retries: {url}") from exc


def _map_rows(
    rows: list[object],
    subcategory: str,
    mapper: Callable[[object, str], IngestRecord],
) -> list[IngestRecord]:
    """Map source rows, skipping poison.

    Args:
        rows: Source objects.
        subcategory: SYS-009 id.
        mapper: Record mapper.

    Returns:
        Ingest records.
    """
    records: list[IngestRecord] = []
    for item in rows:
        try:
            records.append(mapper(item, subcategory))
        except (KeyError, TypeError, ValueError) as exc:
            _LOG.warning("skipping poison patent row: %s", exc)
    return records


def _patent_record(
    patent_id: str,
    title: str,
    published: str,
    subcategory: str,
    abstract: str = "",
    authors: list[str] | None = None,
    keywords: list[str] | None = None,
    claims: list[str] | None = None,
) -> IngestRecord:
    """Build a fixture-shaped patent ingest dict.

    Args:
        patent_id: Office publication number.
        title: Invention title.
        published: ISO date.
        subcategory: SYS-009 id.
        abstract: Abstract text.
        authors: Inventor names.
        keywords: CPC/IPC or topic tokens.
        claims: Claim text when the office provides it.

    Returns:
        Ingest record.
    """
    if not patent_id:
        raise KeyError("patent_id")
    if not title:
        raise KeyError("title")
    if not published:
        raise KeyError("publication_date")
    normalized = _normalize_patent(patent_id)
    return {
        "id": str(uuid5(NAMESPACE_URL, normalized)),
        "kind": "patent",
        "title": title,
        "abstract": abstract,
        "published_on": published,
        "patent": normalized,
        "authors": authors or [],
        "keywords": keywords or [],
        "claims": [claim for claim in (claims or []) if claim],
        "subcategory": subcategory,
        "cites": [],
    }


def _normalize_patent(value: str) -> str:
    """Uppercase a patent number and drop spaces/hyphens.

    Args:
        value: Raw office number.

    Returns:
        Stable identity string.
    """
    return normalize_patent(value)


def _epo_items(payload: object) -> list[object]:
    """Collect EPO search or biblio documents.

    Args:
        payload: OPS JSON.

    Returns:
        Document objects.
    """
    if is_object_list(payload):
        return payload
    if not is_object_dict(payload):
        return []
    if payload.get("results") or payload.get("publications"):
        raw = payload.get("results") or payload.get("publications")
        return list(raw) if is_object_list(raw) else []
    world = payload.get("ops:world-patent-data")
    root = world if is_object_dict(world) else payload
    search = root.get("ops:biblio-search") if is_object_dict(root) else None
    result = search.get("ops:search-result") if is_object_dict(search) else None
    if not is_object_dict(result):
        return []
    docs = result.get("exchange-documents") or result.get("ops:publication-reference")
    return _unwrap_named(
        docs, ("exchange-document", "ops:publication-reference", "document-id")
    )


def _epo_record(item: object, subcategory: str) -> IngestRecord:
    """Map one OPS document.

    Args:
        item: OPS JSON node.
        subcategory: SYS-009 id.

    Returns:
        Ingest record.
    """
    if not is_object_dict(item):
        raise TypeError("epo row must be an object")
    if item.get("patent_id") or item.get("title"):
        return _simple_patent(item, subcategory)
    doc_id = _epo_document_id(item)
    country = _ops_text(doc_id.get("country"))
    number = _ops_text(doc_id.get("doc-number"))
    kind = _ops_text(doc_id.get("kind"))
    patent_id = f"{country}{number}{kind}"
    biblio_raw = item.get("bibliographic-data")
    biblio = biblio_raw if is_object_dict(biblio_raw) else item
    title = _ops_title(biblio) or _ops_text(item.get("invention-title"))
    published = _ops_date(doc_id) or _ops_date(biblio)
    abstract = _ops_text(item.get("abstract") or (biblio or {}).get("abstract"))
    inventors = _ops_inventors(biblio if is_object_dict(biblio) else item)
    keywords = _ops_classes(biblio if is_object_dict(biblio) else item)
    claims = _claim_list(item.get("claims") or (biblio or {}).get("claims"))
    return _patent_record(
        patent_id, title, published, subcategory, abstract, inventors, keywords, claims
    )


def _epo_document_id(item: dict[str, object]) -> dict[str, object]:
    """Find a document-id object.

    Args:
        item: OPS node.

    Returns:
        document-id dict (possibly empty).
    """
    node = item.get("document-id")
    if is_object_dict(node):
        return node
    if is_object_list(node) and node and is_object_dict(node[0]):
        return node[0]
    nested = item.get("bibliographic-data")
    if is_object_dict(nested):
        pub = nested.get("publication-reference")
        if is_object_dict(pub):
            inner = pub.get("document-id")
            if is_object_dict(inner):
                return inner
    return item


def _wipo_items(payload: object) -> list[object]:
    """Collect WIPO JSON result rows.

    Args:
        payload: Gateway JSON.

    Returns:
        Result objects.
    """
    if is_object_list(payload):
        return payload
    if not is_object_dict(payload):
        return []
    for key in ("results", "patents", "docs", "data"):
        raw = payload.get(key)
        if is_object_list(raw):
            return raw
        results = raw.get("results") if is_object_dict(raw) else None
        if is_object_list(results):
            return results
    return []


def _wipo_record(item: object, subcategory: str) -> IngestRecord:
    """Map one PATENTSCOPE JSON record.

    Args:
        item: Gateway object.
        subcategory: SYS-009 id.

    Returns:
        Ingest record.
    """
    if not is_object_dict(item):
        raise TypeError("wipo row must be an object")
    patent_id = str(
        item.get("publicationNumber")
        or item.get("publication_number")
        or item.get("id")
        or item.get("patent")
        or ""
    )
    title = str(item.get("title") or item.get("inventionTitle") or "")
    published = str(
        item.get("publicationDate")
        or item.get("publication_date")
        or item.get("date")
        or ""
    )
    abstract = str(item.get("abstract") or "")
    inventors = _name_list(item.get("inventors") or item.get("authors"))
    keywords = _symbol_list(item.get("ipc") or item.get("cpc") or item.get("keywords"))
    claims = _claim_list(item.get("claims") or item.get("independentClaims"))
    return _patent_record(
        patent_id, title, published, subcategory, abstract, inventors, keywords, claims
    )


def _patsnap_items(payload: object) -> list[object]:
    """Collect PatSnap P002 result rows.

    Args:
        payload: API JSON.

    Returns:
        Result objects.
    """
    if is_object_list(payload):
        return payload
    if not is_object_dict(payload):
        return []
    data = payload.get("data")
    nested = data.get("results") if is_object_dict(data) else None
    if is_object_list(nested):
        return nested
    top = payload.get("results")
    if is_object_list(top):
        return top
    return []


def _patsnap_record(item: object, subcategory: str) -> IngestRecord:
    """Map one PatSnap PatentBase row.

    Args:
        item: Result object.
        subcategory: SYS-009 id.

    Returns:
        Ingest record.
    """
    if not is_object_dict(item):
        raise TypeError("patsnap row must be an object")
    patent_id = str(
        item.get("pn") or item.get("patent_number") or item.get("patent_id") or ""
    )
    title = str(item.get("title") or "")
    published = _patsnap_date(item.get("pbdt") or item.get("publication_date"))
    inventors_raw = item.get("inventor") or item.get("inventors") or ""
    if isinstance(inventors_raw, str):
        inventors = [part.strip() for part in inventors_raw.split("|") if part.strip()]
    else:
        inventors = _name_list(inventors_raw)
    keywords = [str(item["authority"])] if item.get("authority") else []
    abstract = str(item.get("abstract") or "")
    claims = _claim_list(item.get("claims") or item.get("claim"))
    return _patent_record(
        patent_id, title, published, subcategory, abstract, inventors, keywords, claims
    )


def _lens_items(payload: object) -> list[object]:
    """Collect Lens patent hits.

    Args:
        payload: API JSON.

    Returns:
        Hit objects.
    """
    if is_object_list(payload):
        return payload
    if not is_object_dict(payload):
        return []
    data = payload.get("data")
    if is_object_list(data):
        return data
    return []


def _lens_record(item: object, subcategory: str) -> IngestRecord:
    """Map one Lens patent document.

    Args:
        item: Hit object.
        subcategory: SYS-009 id.

    Returns:
        Ingest record.
    """
    if not is_object_dict(item):
        raise TypeError("lens row must be an object")
    jurisdiction = str(item.get("jurisdiction") or "")
    doc_number = str(item.get("doc_number") or "")
    composite = f"{jurisdiction}{doc_number}"
    patent_id = str(item.get("doc_key") or composite or "")
    if not patent_id:
        raise KeyError("patent_id")
    biblio_raw = item.get("biblio")
    biblio: dict[str, object] = biblio_raw if is_object_dict(biblio_raw) else {}
    title = _lens_title(biblio) or str(item.get("title") or "")
    published = str(item.get("date_published") or "")[:10]
    abstract = _lens_abstract(biblio)
    inventors = _lens_inventors(biblio)
    keywords = _lens_cpc(biblio)
    claims = _claim_list(item.get("claims") or biblio.get("claims"))
    return _patent_record(
        patent_id, title, published, subcategory, abstract, inventors, keywords, claims
    )


def _simple_patent(item: dict[str, object], subcategory: str) -> IngestRecord:
    """Map a simplified patent dict.

    Args:
        item: Keys patent_id/title/publication_date.
        subcategory: SYS-009 id.

    Returns:
        Ingest record.
    """
    return _patent_record(
        str(item.get("patent_id") or item.get("patent") or ""),
        str(item.get("title") or ""),
        str(item.get("publication_date") or item.get("published_on") or ""),
        subcategory,
        str(item.get("abstract") or ""),
        _name_list(item.get("authors") or item.get("inventors")),
        _symbol_list(item.get("keywords") or item.get("cpc")),
        _claim_list(item.get("claims")),
    )


def _unwrap_named(node: object, keys: tuple[str, ...]) -> list[object]:
    """Flatten OPS wrapper objects into a list.

    Args:
        node: Dict, list, or None.
        keys: Wrapper key names.

    Returns:
        Child objects.
    """
    if node is None:
        return []
    if is_object_list(node):
        rows: list[object] = []
        for item in node:
            rows.extend(_unwrap_named(item, keys))
        return rows
    if not is_object_dict(node):
        return []
    for key in keys:
        if key in node:
            return _unwrap_named(node[key], keys)
    return [node]


def _ops_text(node: object) -> str:
    """Read OPS JSON text (``$`` leaf or English ``@lang``).

    Args:
        node: String, dict, or list.

    Returns:
        Concatenated text.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if is_object_dict(node):
        if "$" in node:
            return str(node["$"])
        if "p" in node:
            return _ops_text(node["p"])
        english = None
        fallback = ""
        for value in node.values():
            text = _ops_text(value)
            if not text:
                continue
            fallback = fallback or text
            if is_object_dict(value) and str(value.get("@lang", "")).lower().startswith(
                "en"
            ):
                english = text
        return english or fallback
    if is_object_list(node):
        english = ""
        fallback = ""
        for item in node:
            text = _ops_text(item)
            if not text:
                continue
            fallback = fallback or text
            if is_object_dict(item) and str(item.get("@lang", "")).lower().startswith(
                "en"
            ):
                english = text
        return english or fallback
    return str(node)


def _ops_title(biblio: object) -> str:
    """Invention title from bibliographic-data.

    Args:
        biblio: Biblio object.

    Returns:
        Title.
    """
    if not is_object_dict(biblio):
        return ""
    return _ops_text(biblio.get("invention-title"))


def _ops_date(node: object) -> str:
    """ISO date from an OPS document-id or biblio block.

    Args:
        node: Dict with date or document-id.

    Returns:
        YYYY-MM-DD or empty.
    """
    if not is_object_dict(node):
        return ""
    raw = _ops_text(node.get("date"))
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    if len(raw) == 4 and raw.isdigit():
        return f"{raw}-01-01"
    if len(raw) >= 10:
        return raw[:10]
    return ""


def _ops_inventors(biblio: dict[str, object]) -> list[str]:
    """Inventor names from OPS parties.

    Args:
        biblio: Bibliographic-data.

    Returns:
        Names.
    """
    parties = biblio.get("parties") if is_object_dict(biblio.get("parties")) else biblio
    inventors = parties.get("inventors") if is_object_dict(parties) else None
    rows = _unwrap_named(inventors, ("inventor",))
    names: list[str] = []
    for row in rows:
        if not is_object_dict(row):
            continue
        name = _ops_text(row.get("inventor-name") or row.get("name"))
        if name:
            names.append(name)
    return names


def _ops_classes(biblio: dict[str, object]) -> list[str]:
    """CPC/IPC symbols from OPS classifications.

    Args:
        biblio: Bibliographic-data.

    Returns:
        Class symbols.
    """
    block = biblio.get("classifications-cpc") or biblio.get("patent-classifications")
    rows = _unwrap_named(block, ("classification-cpc", "patent-classification"))
    symbols: list[str] = []
    for row in rows:
        if not is_object_dict(row):
            continue
        symbol = _ops_text(row.get("symbol") or row.get("classification-symbol"))
        if symbol:
            symbols.append(symbol)
    return symbols


def _patsnap_date(value: object) -> str:
    """Convert PatSnap YYYYMMDD integers.

    Args:
        value: Int or string date.

    Returns:
        ISO date.
    """
    if value is None:
        return ""
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text[:10]


def _lens_title(biblio: dict[str, object]) -> str:
    """English invention title from Lens biblio.

    Args:
        biblio: Lens biblio object.

    Returns:
        Title.
    """
    titles = biblio.get("invention_title")
    if not is_object_list(titles):
        return ""
    english = ""
    fallback = ""
    for row in titles:
        if not is_object_dict(row):
            continue
        text = str(row.get("text") or "")
        if not text:
            continue
        fallback = fallback or text
        if str(row.get("lang", "")).lower().startswith("en"):
            english = text
    return english or fallback


def _lens_abstract(biblio: dict[str, object]) -> str:
    """Abstract text from Lens biblio when present.

    Args:
        biblio: Lens biblio object.

    Returns:
        Abstract.
    """
    abstracts = biblio.get("abstracts") or biblio.get("abstract")
    if isinstance(abstracts, str):
        return abstracts
    if is_object_dict(abstracts):
        return str(abstracts.get("text") or "")
    if is_object_list(abstracts):
        for row in abstracts:
            if is_object_dict(row) and str(row.get("lang", "")).lower().startswith(
                "en"
            ):
                return str(row.get("text") or "")
            if is_object_dict(row) and row.get("text"):
                return str(row["text"])
    return ""


def _lens_inventors(biblio: dict[str, object]) -> list[str]:
    """Inventor names from Lens parties.

    Args:
        biblio: Lens biblio object.

    Returns:
        Names.
    """
    parties = biblio.get("parties") if is_object_dict(biblio.get("parties")) else {}
    inventors = parties.get("inventors") if is_object_dict(parties) else []
    names: list[str] = []
    if not is_object_list(inventors):
        return names
    for row in inventors:
        if not is_object_dict(row):
            continue
        extracted_raw = row.get("extracted_name")
        extracted = extracted_raw if is_object_dict(extracted_raw) else {}
        name = extracted.get("value") if extracted else row.get("name")
        if name:
            names.append(str(name))
    return names


def _lens_cpc(biblio: dict[str, object]) -> list[str]:
    """CPC symbols from Lens biblio.

    Args:
        biblio: Lens biblio object.

    Returns:
        Symbols.
    """
    block = biblio.get("classifications_cpc")
    if not is_object_dict(block):
        return []
    rows = block.get("classifications")
    if not is_object_list(rows):
        return []
    return [
        str(row["symbol"]) for row in rows if is_object_dict(row) and row.get("symbol")
    ]


def _name_list(raw: object) -> list[str]:
    """Inventor names from strings or objects.

    Args:
        raw: List of strings or dicts.

    Returns:
        Names.
    """
    names: list[str] = []
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if not is_object_list(raw):
        return names
    for row in raw:
        if isinstance(row, str):
            names.append(row)
        elif is_object_dict(row):
            name = row.get("name") or row.get("display_name") or row.get("value")
            if name:
                names.append(str(name))
    return names


def _symbol_list(raw: object) -> list[str]:
    """Classification symbols from mixed lists.

    Args:
        raw: Strings or dicts with symbol.

    Returns:
        Symbols.
    """
    symbols: list[str] = []
    if not is_object_list(raw):
        return symbols
    for row in raw:
        if isinstance(row, str):
            symbols.append(row)
        elif is_object_dict(row):
            symbol = row.get("symbol") or row.get("code") or row.get("display_name")
            if symbol:
                symbols.append(str(symbol))
    return symbols


def _claim_list(raw: object) -> list[str]:
    """Claim text from strings or objects.

    Args:
        raw: Claim strings, dicts with claim_text/text, or a single string.

    Returns:
        Claim strings.
    """
    claims: list[str] = []
    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else claims
    if not is_object_list(raw):
        return claims
    for row in raw:
        if isinstance(row, str) and row.strip():
            claims.append(row.strip())
        elif is_object_dict(row):
            text = str(
                row.get("claim_text") or row.get("text") or row.get("value") or ""
            ).strip()
            if text:
                claims.append(text)
    return claims
