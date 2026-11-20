"""Upload, bibliography matching, and generate context assembly."""

from __future__ import annotations

from datetime import date, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from delphi_contracts.batch import BatchCheckRequest
from delphi_contracts.category import Category
from delphi_contracts.enums import (
    CategoryScheme,
    EdgeKind,
    IdentityKind,
    NeighborhoodMode,
    SubcategoryId,
    WorkKind,
)
from delphi_contracts.extraction import CONSENT_DESTINATION, BibliographyEntry, Extraction
from delphi_contracts.graph import Edge
from delphi_contracts.identity import Identity
from delphi_contracts.mask import dropped_ids
from delphi_contracts.neighborhood import Neighborhood
from delphi_contracts.paths import MaskedContext, PathProposal, PathRequest
from delphi_contracts.work import Work

from delphi.catalog import Catalog, has_subcategory
from delphi.ports import Embedder, Extractor, Generator

__all__ = [
    "ConsentError",
    "MissingDependencyError",
    "attach_bibliography",
    "build_masked_context",
    "generate_paths",
    "require_consent",
    "upload_pdf",
    "work_from_extraction",
]


_UNKNOWN_DATE = date(1970, 1, 1)


class ConsentError(ValueError):
    """Raised when PDF bytes arrive without naming Delphi as destination."""


class MissingDependencyError(RuntimeError):
    """Raised when generate or upload is called without a wired collaborator."""


def require_consent(destination: str) -> None:
    """Reject uploads that do not name Delphi.

    Args:
        destination: Consent destination string.

    """
    if destination != CONSENT_DESTINATION:
        raise ConsentError("consent must name delphi as destination")


def work_from_extraction(extraction: Extraction, subcategory: str) -> Work:
    """Build a catalog work from an extraction.

    Args:
        extraction: Structured PDF fields.
        subcategory: User-confirmed or suggested subcategory.

    Returns:
        Work ready to upsert.
    """
    published = extraction.published_on or _UNKNOWN_DATE
    categories = extraction.suggested_categories or _category_for(subcategory)
    identities = extraction.identities or (
        Identity(kind=IdentityKind.CONTENT_HASH, value=extraction.content_hash),
    )
    return Work(
        id=extraction.id,
        kind=WorkKind.PAPER,
        title=extraction.title,
        authors=extraction.authors,
        keywords=extraction.keywords,
        abstract=extraction.body_text[:500],
        published_on=published,
        identities=identities,
        categories=categories,
    )


def attach_bibliography(
    catalog: Catalog,
    from_work: UUID,
    entries: tuple[BibliographyEntry, ...],
) -> tuple[BibliographyEntry, ...]:
    """Match bibliography rows and write cites edges.

    Args:
        catalog: Work store.
        from_work: Citing work id.
        entries: Extracted bibliography.

    Returns:
        Entries with matched_work_id filled when known.
    """
    resolved: list[BibliographyEntry] = []
    for entry in entries:
        matched = _match_entry(catalog, entry)
        resolved.append(matched)
        if matched.matched_work_id is not None:
            catalog.add_edge(
                Edge(from_work=from_work, to_work=matched.matched_work_id, kind=EdgeKind.CITES)
            )
    return tuple(resolved)


def upload_pdf(
    catalog: Catalog,
    pdf_bytes: bytes,
    filename: str,
    destination: str,
    subcategory: str,
    extractor: Extractor | None,
    embedder: Embedder | None,
) -> tuple[Extraction, Neighborhood]:
    """Consent, extract, upsert, cite, embed, and return a union neighborhood.

    Args:
        catalog: Store.
        pdf_bytes: PDF content.
        filename: Original name.
        destination: Consent destination.
        subcategory: Filter used for the content graph.
        extractor: Daedalus extractor.
        embedder: Daedalus embedder.

    Returns:
        Stored extraction and union neighborhood.

    """
    require_consent(destination)
    if extractor is None or embedder is None:
        raise MissingDependencyError("upload requires extractor and embedder")
    digest = content_hash(pdf_bytes)
    existing = catalog.get_extraction_by_hash(digest)
    if existing is not None:
        work = catalog.get_work(existing.id) or work_from_extraction(existing, subcategory)
        catalog.upsert_work(work)
        resolved = attach_bibliography(catalog, work.id, existing.bibliography)
        extraction = existing.model_copy(update={"bibliography": resolved})
        catalog.put_extraction(extraction)
        embedder.embed_and_link(work, extraction.body_text)
        neighborhood = catalog.neighborhood(work.id, NeighborhoodMode.UNION, subcategory)
        return extraction, neighborhood
    extraction = extractor.extract(pdf_bytes, filename)
    if not extraction.suggested_categories:
        extraction = extraction.model_copy(
            update={"suggested_categories": _category_for(subcategory)}
        )
    catalog.put_extraction(extraction)
    work = work_from_extraction(extraction, subcategory)
    catalog.upsert_work(work)
    resolved = attach_bibliography(catalog, work.id, extraction.bibliography)
    extraction = extraction.model_copy(update={"bibliography": resolved})
    catalog.put_extraction(extraction)
    embedder.embed_and_link(work, extraction.body_text)
    neighborhood = catalog.neighborhood(work.id, NeighborhoodMode.UNION, subcategory)
    return extraction, neighborhood


def build_masked_context(
    catalog: Catalog,
    request: PathRequest,
    held_out_ids: tuple[UUID, ...] = (),
) -> MaskedContext:
    """Build a generate context from the catalog.

    Args:
        catalog: Store.
        request: Generate request.
        held_out_ids: Ids Epimetheus wants hidden.

    Returns:
        MaskedContext for Prometheus.

    """
    seed = _seed_work(catalog, request)
    if not has_subcategory(seed, request.subcategory):
        raise ValueError("seed is not in the requested subcategory")
    mask_on, inclusive_as_of, blocked = _mask_bounds(catalog, request, seed, held_out_ids)
    neighborhood = catalog.neighborhood(
        seed.id,
        NeighborhoodMode.UNION,
        request.subcategory,
        as_of=inclusive_as_of,
        excluded_ids=blocked,
    )
    return MaskedContext(
        seed=seed,
        mask_on=mask_on,
        held_out_ids=held_out_ids,
        neighborhood=neighborhood,
        subcategory=request.subcategory,
        kind=request.kind,
    )


def generate_paths(
    catalog: Catalog,
    request: PathRequest,
    generator: Generator | None,
    held_out_ids: tuple[UUID, ...] = (),
) -> tuple[PathProposal, ...]:
    """Assemble context and call the generator.

    Args:
        catalog: Store.
        request: Generate request.
        generator: Prometheus adapter.
        held_out_ids: Optional hindcast exclusions.

    Returns:
        Ranked proposals.

    """
    if generator is None:
        raise MissingDependencyError("generate requires a generator")
    context = build_masked_context(catalog, request, held_out_ids)
    return generator.generate(context)


def content_hash(data: bytes) -> str:
    """Return SHA-256 hex of bytes.

    Args:
        data: Raw bytes.

    Returns:
        Hex digest.
    """
    return sha256(data).hexdigest()


def work_id_for(identity: Identity) -> UUID:
    """Stable UUID from an identity pair.

    Args:
        identity: External identifier.

    Returns:
        UUID5.
    """
    return uuid5(NAMESPACE_URL, f"{identity.kind}:{identity.value}")


def _mask_bounds(
    catalog: Catalog,
    request: PathRequest,
    seed: Work,
    held_out_ids: tuple[UUID, ...],
) -> tuple[date, date, frozenset[UUID]]:
    """Return the first forbidden date, the inclusive neighborhood bound, and drops.

    ``mask_on`` is the first date that counts as future (``published_on >= mask_on``).
    The catalog ``as_of`` argument stays inclusive, so it is the day before ``mask_on``.
    An undated seed never opens the filter.

    Args:
        catalog: Store.
        request: Generate request.
        seed: Resolved seed work.
        held_out_ids: Ids Epimetheus wants hidden.

    Returns:
        First forbidden date, inclusive neighborhood bound, and excluded ids.

    Raises:
        KeyError: A held-out id is not in the catalog.
        ValueError: The seed has no publication date and the request has no ``as_of``.
    """
    if held_out_ids:
        cuts: list[date] = []
        for hid in held_out_ids:
            held = catalog.get_work(hid)
            if held is None:
                raise KeyError(f"held-out work not found: {hid}")
            if held.published_on == _UNKNOWN_DATE:
                raise ValueError("held-out work has no publication date")
            cuts.append(held.published_on)
        mask_on = request.as_of or min(cuts)
        blocked: set[UUID] = set()
        for hid in held_out_ids:
            blocked |= dropped_ids(catalog.list_works(), catalog.edges(), hid, mask_on)
        blocked.discard(seed.id)
        return mask_on, mask_on - timedelta(days=1), frozenset(blocked)
    last_allowed = request.as_of or seed.published_on
    if last_allowed == _UNKNOWN_DATE:
        raise ValueError("seed has no publication date; pass as_of")
    return last_allowed + timedelta(days=1), last_allowed, frozenset()


def _seed_work(catalog: Catalog, request: PathRequest) -> Work:
    """Resolve seed work or extraction.

    Args:
        catalog: Store.
        request: Generate request.

    Returns:
        Seed work.

    """
    if request.seed_work_id is not None:
        work = catalog.get_work(request.seed_work_id)
        if work is not None:
            return work
    if request.extraction_id is not None:
        extraction = catalog.get_extraction(request.extraction_id)
        if extraction is not None:
            stored = catalog.get_work(extraction.id)
            if stored is not None:
                return stored
    raise KeyError("seed work not found")


def _match_entry(catalog: Catalog, entry: BibliographyEntry) -> BibliographyEntry:
    """Resolve one bibliography row via batch-check.

    Args:
        catalog: Store.
        entry: Extracted cite.

    Returns:
        Entry with matched_work_id when known.
    """
    if entry.identity is None:
        return entry
    response = catalog.batch_check(BatchCheckRequest(identities=(entry.identity,)))
    row = response.rows[0]
    if not row.known:
        return entry
    return entry.model_copy(update={"matched_work_id": row.work_id})


def _category_for(subcategory: str) -> tuple[Category, ...]:
    """Build a default category tuple.

    Args:
        subcategory: SYS-009 id.

    Returns:
        One Category tagged with that subcategory.
    """
    label = subcategory.replace("_", " ")
    try:
        parsed = SubcategoryId(subcategory)
    except ValueError:
        parsed = None
    return (
        Category(
            scheme=CategoryScheme.OPENALEX_TOPIC,
            code=subcategory,
            label=label,
            subcategory=parsed,
        ),
    )
