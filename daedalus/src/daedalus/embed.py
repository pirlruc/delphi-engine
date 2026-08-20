"""Content-graph embeddings against other papers."""

from __future__ import annotations

from delphi_contracts.enums import WorkKind
from delphi_contracts.llm import EmbedRequest, LlmProvider, build_provider
from delphi_contracts.work import Work

from daedalus.ports import CatalogWriter

__all__ = ["HashEmbedder", "chunk_text", "compose_embed_text", "mean_pool"]

_PAPER_PREFIX = "Represent this scientific paper for nearest-neighbor retrieval:\n"
_PATENT_PREFIX = "Represent this patent for nearest-neighbor retrieval:\n"
_SEP = "\n\n"
_CHUNK_CHARS = 12_000
_MAX_EXTRA_CHARS = 24_000


def compose_embed_text(work: Work, extra: str = "") -> str:
    """Build the canonical embedding string for a catalog work.

    Title and abstract are always included. Patents add CPC/keywords and
    claims. Uploaded body is appended when it is not a duplicate of the
    catalog fields. Kind-specific instruction prefixes help instruction-tuned
    embedders; they do not change Fake hashing except as more tokens.

    Args:
        work: Catalog work.
        extra: Extracted body or other long text. Ignored when it only
            restates title plus abstract.

    Returns:
        Text to embed (possibly longer than one model window).
    """
    prefix = _PATENT_PREFIX if work.kind is WorkKind.PATENT else _PAPER_PREFIX
    parts = [work.title.strip()]
    abstract = work.abstract.strip()
    if abstract:
        parts.append(abstract)
    if work.keywords:
        label = "CPC" if work.kind is WorkKind.PATENT else "keywords"
        parts.append(f"{label}: {', '.join(work.keywords)}")
    if work.claims:
        parts.append("claims: " + " ".join(claim.strip() for claim in work.claims if claim.strip()))
    extra_clean = _clip(" ".join(extra.split()), _MAX_EXTRA_CHARS)
    if extra_clean and not _redundant_catalog_text(work, extra_clean):
        parts.append(extra_clean)
    return prefix + _SEP.join(part for part in parts if part)


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
    if not aligned:
        return ()
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
        composed = compose_embed_text(work, extra=text)
        vector, model = self._embed_pooled(composed)
        self._catalog.put_embedding(work.id, vector, model)
        self._catalog.rebuild_similar_to(work.id)

    def _embed_pooled(self, text: str) -> tuple[tuple[float, ...], str]:
        """Embed one window, or mean-pool chunks when over the size cap.

        Args:
            text: Composed embedding string.

        Returns:
            Vector and model id.
        """
        windows = chunk_text(text) or [text or "empty"]
        if len(windows) == 1:
            response = self._llm.embed(EmbedRequest(text=windows[0]))
            return response.vector, response.model
        responses = [self._llm.embed(EmbedRequest(text=window)) for window in windows]
        pooled = mean_pool([item.vector for item in responses])
        model = responses[0].model
        return pooled or responses[0].vector, model


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
