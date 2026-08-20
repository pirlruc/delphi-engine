"""Content-graph embeddings against other papers."""

from __future__ import annotations

from delphi_contracts.enums import IdentityKind, WorkKind
from delphi_contracts.llm import EmbedRequest, LlmProvider, build_provider
from delphi_contracts.work import Work

from daedalus.ports import CatalogWriter

__all__ = [
    "HashEmbedder",
    "chunk_text",
    "compose_embed_text",
    "contextual_windows",
    "mean_pool",
]

_PAPER_PREFIX = "Represent this scientific paper for nearest-neighbor retrieval:\n"
_PATENT_PREFIX = "Represent this patent for nearest-neighbor retrieval:\n"
_SEP = "\n\n"
_CHUNK_CHARS = 12_000
_MAX_EXTRA_CHARS = 24_000
_MAX_CLAIM_COUNT = 3
_MAX_CLAIMS_CHARS = 4_000
_MIN_TAIL_BUDGET = 256
_ID_KINDS = frozenset(
    {IdentityKind.DOI, IdentityKind.ARXIV, IdentityKind.PATENT},
)


def compose_embed_text(work: Work, extra: str = "") -> str:
    """Build the canonical embedding string for a catalog work.

    Title, abstract, public identifiers, and CPC/keywords are the mixed-graph
    core (papers have no claims). Patents may add a **capped** claim block so
    legalese does not drown the abstract. Uploaded body is appended when it is
    not a duplicate of the catalog fields.

    Args:
        work: Catalog work.
        extra: Extracted body or other long text. Ignored when it only
            restates title plus abstract.

    Returns:
        Text to embed (possibly longer than one model window).
    """
    header = _compose_header(work)
    tail = _compose_tail(work, extra)
    return header if not tail else header + _SEP + tail


def contextual_windows(work: Work, extra: str = "", size: int = _CHUNK_CHARS) -> list[str]:
    """Chunk long tails while repeating title and abstract on every window.

    Args:
        work: Catalog work.
        extra: Optional extracted body.
        size: Maximum characters per window.

    Returns:
        One or more strings to embed, then mean-pool.
    """
    composed = compose_embed_text(work, extra=extra)
    if len(composed) <= size:
        return [composed]
    header = _compose_header(work)
    tail = composed[len(header) :].lstrip()
    if not tail:
        return chunk_text(header, size=size) or [header]
    budget = size - len(header) - len(_SEP)
    if budget < _MIN_TAIL_BUDGET:
        title_tag = _kind_prefix(work) + work.title.strip() + _SEP
        room = max(size - len(title_tag), _MIN_TAIL_BUDGET)
        pieces = chunk_text(composed, size=room)
        return [
            piece if piece.startswith(_kind_prefix(work)) else title_tag + piece for piece in pieces
        ]
    return [header + _SEP + piece for piece in chunk_text(tail, size=budget)]


def chunk_text(text: str, size: int = _CHUNK_CHARS) -> list[str]:
    """Split text into windows, preferring paragraph boundaries.

    Args:
        text: Source string.
        size: Maximum characters per chunk.

    Returns:
        Non-empty chunks. A single element when ``text`` fits.
    """
    stripped = text.strip()
    if not stripped:
        return []
    if len(stripped) <= size:
        return [stripped]
    paragraphs = [part.strip() for part in stripped.split("\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs or [stripped]:
        candidate = f"{current}\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= size:
            current = paragraph
            continue
        for start in range(0, len(paragraph), size):
            piece = paragraph[start : start + size]
            if piece:
                chunks.append(piece)
        current = ""
    if current:
        chunks.append(current)
    return chunks or [stripped[:size]]


def mean_pool(vectors: list[tuple[float, ...]]) -> tuple[float, ...]:
    """Average equal-length embedding vectors.

    Args:
        vectors: Chunk embeddings. Empty or mismatched rows are skipped.

    Returns:
        Mean vector. Empty when nothing can be pooled.
    """
    usable = [row for row in vectors if row]
    if not usable:
        return ()
    dim = len(usable[0])
    aligned = [row for row in usable if len(row) == dim]
    acc = [0.0] * dim
    for row in aligned:
        for index, value in enumerate(row):
            acc[index] += value
    scale = float(len(aligned))
    return tuple(value / scale for value in acc)


class HashEmbedder:
    """Embed catalog or upload text and refresh similar_to edges."""

    def __init__(self, catalog: CatalogWriter, llm: LlmProvider | None = None) -> None:
        """Store catalog and provider.

        Args:
            catalog: Writer with embedding storage.
            llm: SYS-006 adapter. Defaults to Fake hashing embed.
        """
        self._catalog = catalog
        self._llm = llm or build_provider()

    def embed_and_link(self, work: Work, text: str = "") -> None:
        """Embed composed catalog text (plus optional body) and rebuild edges.

        Args:
            work: Catalog work.
            text: Optional extracted body. Title+abstract-only strings are
                treated as empty so old call sites do not duplicate fields.
        """
        windows = contextual_windows(work, extra=text)
        vector, model = self._embed_pooled(windows)
        self._catalog.put_embedding(work.id, vector, model)
        self._catalog.rebuild_similar_to(work.id)

    def _embed_pooled(self, windows: list[str]) -> tuple[tuple[float, ...], str]:
        """Embed one window, or mean-pool chunks when over the size cap.

        Args:
            windows: Contextual embedding strings.

        Returns:
            Vector and model id.
        """
        texts = windows or ["empty"]
        if len(texts) == 1:
            response = self._llm.embed(EmbedRequest(text=texts[0]))
            return response.vector, response.model
        responses = [self._llm.embed(EmbedRequest(text=window)) for window in texts]
        pooled = mean_pool([item.vector for item in responses])
        model = responses[0].model
        return pooled or responses[0].vector, model


def _kind_prefix(work: Work) -> str:
    """Return the instruction prefix for a work kind.

    Args:
        work: Catalog work.

    Returns:
        Retrieval instruction line including a trailing newline.
    """
    return _PATENT_PREFIX if work.kind is WorkKind.PATENT else _PAPER_PREFIX


def _compose_header(work: Work) -> str:
    """Title, abstract, identifiers, and CPC — the paper/patent bridge.

    Args:
        work: Catalog work.

    Returns:
        Prefix plus semantic-core fields.
    """
    parts = [work.title.strip()]
    abstract = work.abstract.strip()
    if abstract:
        parts.append(abstract)
    identifiers = [
        item.value.strip()
        for item in work.identities
        if item.kind in _ID_KINDS and item.value.strip()
    ]
    if identifiers:
        parts.append("ids: " + ", ".join(identifiers))
    if work.keywords:
        label = "CPC" if work.kind is WorkKind.PATENT else "keywords"
        parts.append(f"{label}: {', '.join(work.keywords)}")
    return _kind_prefix(work) + _SEP.join(part for part in parts if part)


def _compose_tail(work: Work, extra: str) -> str:
    """Capped claims and optional body that is not catalog duplication.

    Args:
        work: Catalog work.
        extra: Extracted body.

    Returns:
        Tail string, possibly empty.
    """
    parts: list[str] = []
    claims = _capped_claims(work)
    if claims:
        parts.append(claims)
    extra_clean = _clip(" ".join(extra.split()), _MAX_EXTRA_CHARS)
    if extra_clean and not _redundant_catalog_text(work, extra_clean):
        parts.append(extra_clean)
    return _SEP.join(parts)


def _capped_claims(work: Work) -> str:
    """Keep the first independent-style claims without drowning the abstract.

    Args:
        work: Catalog work.

    Returns:
        Claim block or empty string.
    """
    claims = [claim.strip() for claim in work.claims if claim.strip()][:_MAX_CLAIM_COUNT]
    if not claims:
        return ""
    return "claims: " + _clip(" ".join(claims), _MAX_CLAIMS_CHARS)


def _redundant_catalog_text(work: Work, extra: str) -> bool:
    """Return whether extra only restates title plus abstract.

    Args:
        work: Catalog work.
        extra: Candidate extra text.

    Returns:
        True when extra should be dropped.
    """
    compact = _norm(extra)
    baseline = _norm(f"{work.title} {work.abstract}")
    return bool(compact) and compact == baseline


def _clip(text: str, limit: int) -> str:
    """Keep the head of a long extra string.

    Args:
        text: Source.
        limit: Max characters.

    Returns:
        Possibly truncated text.
    """
    if len(text) <= limit:
        return text
    return text[:limit]


def _norm(text: str) -> str:
    """Collapse whitespace for duplicate detection.

    Args:
        text: Source.

    Returns:
        Lowercased collapsed string.
    """
    return " ".join(text.split()).lower()
