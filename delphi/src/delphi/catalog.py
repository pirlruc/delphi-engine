"""Catalog protocol and in-memory implementation."""

from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from delphi_contracts.batch import BatchCheckRequest, BatchCheckResponse, BatchCheckRow
from delphi_contracts.enums import EdgeKind, NeighborDirection, NeighborhoodMode
from delphi_contracts.extraction import Extraction
from delphi_contracts.graph import Edge
from delphi_contracts.identity import Identity
from delphi_contracts.llm import cosine
from delphi_contracts.neighborhood import Neighbor, Neighborhood
from delphi_contracts.work import Work

__all__ = ["Catalog", "MemoryCatalog", "has_subcategory", "scored_neighbors"]


class Catalog(Protocol):
    """Work, edge, embedding, and extraction store."""

    def upsert_work(self, work: Work) -> Work:
        """Insert or replace a work.

        Args:
            work: Record to store.

        Returns:
            The stored work.
        """

    def get_work(self, work_id: UUID) -> Work | None:
        """Return a work by id.

        Args:
            work_id: Catalog UUID.

        Returns:
            The work, or None.
        """

    def batch_check(self, request: BatchCheckRequest) -> BatchCheckResponse:
        """Exact-identifier existence check.

        Args:
            request: Identities in caller order.

        Returns:
            Known/unknown rows in the same order.
        """

    def add_edge(self, edge: Edge) -> None:
        """Store a directed edge, ignoring duplicates.

        Args:
            edge: cites or similar_to row.
        """

    def edges(self, kind: EdgeKind | None = None) -> tuple[Edge, ...]:
        """Return stored edges.

        Args:
            kind: Optional kind filter.

        Returns:
            Matching edges.
        """

    def put_embedding(self, work_id: UUID, vector: tuple[float, ...], model_id: str) -> None:
        """Store an embedding for a work.

        Args:
            work_id: Catalog UUID.
            vector: Dense vector.
            model_id: Embedding model id.
        """

    def get_embedding(self, work_id: UUID) -> tuple[float, ...] | None:
        """Return a stored embedding.

        Args:
            work_id: Catalog UUID.

        Returns:
            Vector or None.
        """

    def list_works(self) -> tuple[Work, ...]:
        """Return every work.

        Returns:
            Catalog works.
        """

    def put_extraction(self, extraction: Extraction) -> Extraction:
        """Store extraction output.

        Args:
            extraction: Structured PDF fields.

        Returns:
            The stored extraction.
        """

    def get_extraction(self, extraction_id: UUID) -> Extraction | None:
        """Return an extraction by id.

        Args:
            extraction_id: Extraction UUID.

        Returns:
            Extraction or None.
        """

    def get_extraction_by_hash(self, content_hash: str) -> Extraction | None:
        """Return an extraction by PDF content hash.

        Args:
            content_hash: SHA-256 hex of the PDF bytes.

        Returns:
            Extraction or None.
        """

    def neighborhood(
        self,
        seed_id: UUID,
        mode: NeighborhoodMode,
        subcategory: str,
        as_of: date | None = None,
        excluded_ids: frozenset[UUID] | None = None,
        k: int = 8,
    ) -> Neighborhood:
        """Return dated neighbors tagged by edge kind.

        Args:
            seed_id: Center work.
            mode: citation, content, or union.
            subcategory: Required SYS-009 filter.
            as_of: Inclusive publication bound.
            excluded_ids: Extra ids to drop (hindcast).
            k: Max similar_to neighbors per direction.

        Returns:
            Neighborhood around the seed.

        """

    def rebuild_similar_to(self, work_id: UUID, k: int = 8) -> None:
        """Replace similar_to edges for a work from stored embeddings.

        Args:
            work_id: Work to refresh.
            k: Neighbor count.
        """

    def rebuild_all_similar_to(self, k: int = 8) -> None:
        """Recompute every similar_to edge from current embeddings.

        Args:
            k: Neighbor count per work.
        """


def has_subcategory(work: Work, subcategory: str) -> bool:
    """Return whether a work is tagged with a subcategory id.

    Args:
        work: Catalog work.
        subcategory: SYS-009 id.

    Returns:
        True when any category.subcategory matches.
    """
    return any(category.subcategory == subcategory for category in work.categories)


class MemoryCatalog:
    """In-memory Catalog used by tests and the prototype server."""

    def __init__(self) -> None:
        """Create empty indexes."""
        self._works: dict[UUID, Work] = {}
        self._identities: dict[tuple[str, str], UUID] = {}
        self._edges: list[Edge] = []
        self._embeddings: dict[UUID, tuple[float, ...]] = {}
        self._models: dict[UUID, str] = {}
        self._extractions: dict[UUID, Extraction] = {}

    def upsert_work(self, work: Work) -> Work:
        """Insert or replace a work.

        Args:
            work: Record to store.

        Returns:
            The stored work.
        """
        for identity in work.identities:
            key = (identity.kind.value, identity.value)
            owner = self._identities.get(key)
            if owner is not None and owner != work.id:
                raise ValueError(
                    f"identity {identity.kind.value}:{identity.value} belongs to another work"
                )
        self._works[work.id] = work
        stale = [key for key, owner in self._identities.items() if owner == work.id]
        for key in stale:
            del self._identities[key]
        for identity in work.identities:
            self._identities[(identity.kind.value, identity.value)] = work.id
        return work

    def get_work(self, work_id: UUID) -> Work | None:
        """Return a work by id.

        Args:
            work_id: Catalog UUID.

        Returns:
            The work, or None.
        """
        return self._works.get(work_id)

    def batch_check(self, request: BatchCheckRequest) -> BatchCheckResponse:
        """Exact-identifier existence check.

        Args:
            request: Identities in caller order.

        Returns:
            Known/unknown rows in the same order.
        """
        rows = tuple(_row_for(identity, self._identities) for identity in request.identities)
        return BatchCheckResponse(rows=rows)

    def add_edge(self, edge: Edge) -> None:
        """Store a directed edge, ignoring duplicates and self-loops.

        Args:
            edge: cites or similar_to row.
        """
        if edge.from_work == edge.to_work:
            return
        for index, existing in enumerate(self._edges):
            same = (
                existing.from_work == edge.from_work
                and existing.to_work == edge.to_work
                and existing.kind is edge.kind
            )
            if same:
                self._edges[index] = edge
                return
        self._edges.append(edge)

    def edges(self, kind: EdgeKind | None = None) -> tuple[Edge, ...]:
        """Return stored edges.

        Args:
            kind: Optional kind filter.

        Returns:
            Matching edges.
        """
        if kind is None:
            return tuple(self._edges)
        return tuple(edge for edge in self._edges if edge.kind is kind)

    def put_embedding(self, work_id: UUID, vector: tuple[float, ...], model_id: str) -> None:
        """Store an embedding for a work.

        Args:
            work_id: Catalog UUID.
            vector: Dense vector.
            model_id: Embedding model id.
        """
        self._embeddings[work_id] = vector
        self._models[work_id] = model_id

    def get_embedding(self, work_id: UUID) -> tuple[float, ...] | None:
        """Return a stored embedding.

        Args:
            work_id: Catalog UUID.

        Returns:
            Vector or None.
        """
        return self._embeddings.get(work_id)

    def list_works(self) -> tuple[Work, ...]:
        """Return every work.

        Returns:
            Catalog works.
        """
        return tuple(self._works.values())

    def put_extraction(self, extraction: Extraction) -> Extraction:
        """Store extraction output.

        Args:
            extraction: Structured PDF fields.

        Returns:
            The stored extraction.
        """
        self._extractions[extraction.id] = extraction
        return extraction

    def get_extraction(self, extraction_id: UUID) -> Extraction | None:
        """Return an extraction by id.

        Args:
            extraction_id: Extraction UUID.

        Returns:
            Extraction or None.
        """
        return self._extractions.get(extraction_id)

    def get_extraction_by_hash(self, content_hash: str) -> Extraction | None:
        """Return an extraction by PDF content hash.

        Args:
            content_hash: SHA-256 hex of the PDF bytes.

        Returns:
            Extraction or None.
        """
        for extraction in self._extractions.values():
            if extraction.content_hash == content_hash:
                return extraction
        return None

    def neighborhood(
        self,
        seed_id: UUID,
        mode: NeighborhoodMode,
        subcategory: str,
        as_of: date | None = None,
        excluded_ids: frozenset[UUID] | None = None,
        k: int = 8,
    ) -> Neighborhood:
        """Return dated neighbors tagged by edge kind.

        Args:
            seed_id: Center work.
            mode: citation, content, or union.
            subcategory: Required SYS-009 filter.
            as_of: Inclusive publication bound.
            excluded_ids: Extra ids to drop (hindcast).
            k: Max similar_to neighbors per direction.

        Returns:
            Neighborhood around the seed.

        """
        seed = self._works[seed_id]
        blocked = excluded_ids or frozenset()
        handlers = {
            NeighborhoodMode.CITATION: self._citation_neighbors,
            NeighborhoodMode.CONTENT: self._content_neighbors,
            NeighborhoodMode.UNION: self._union_neighbors,
        }
        neighbors = handlers[mode](seed, subcategory, as_of, blocked, k)
        return Neighborhood(seed=seed, mode=mode, neighbors=neighbors)

    def rebuild_similar_to(self, work_id: UUID, k: int = 8) -> None:
        """Replace similar_to edges for a work from stored embeddings.

        Args:
            work_id: Work to refresh.
            k: Neighbor count.
        """
        source = self._embeddings.get(work_id)
        if source is None:
            return
        self._replace_similar_to(
            work_id,
            scored_neighbors(
                work_id, source, self._embeddings, self._models, self._models.get(work_id)
            ),
            k,
        )

    def rebuild_all_similar_to(self, k: int = 8) -> None:
        """Recompute every similar_to edge from current embeddings.

        Args:
            k: Neighbor count per work.
        """
        self._edges = [edge for edge in self._edges if edge.kind is not EdgeKind.SIMILAR_TO]
        for work_id, source in self._embeddings.items():
            ranked = scored_neighbors(
                work_id, source, self._embeddings, self._models, self._models.get(work_id)
            )
            for other_id, score in ranked[:k]:
                self.add_edge(
                    Edge(from_work=work_id, to_work=other_id, kind=EdgeKind.SIMILAR_TO, score=score)
                )
                self.add_edge(
                    Edge(from_work=other_id, to_work=work_id, kind=EdgeKind.SIMILAR_TO, score=score)
                )

    def _replace_similar_to(self, work_id: UUID, ranked: list[tuple[UUID, float]], k: int) -> None:
        """Drop this work's outgoing similar_to edges, then write its top-k pairs.

        Args:
            work_id: Work to refresh.
            ranked: Scored neighbors.
            k: Neighbor count.
        """
        self._edges = [
            edge
            for edge in self._edges
            if edge.kind is not EdgeKind.SIMILAR_TO or edge.from_work != work_id
        ]
        for other_id, score in ranked[:k]:
            self.add_edge(
                Edge(from_work=work_id, to_work=other_id, kind=EdgeKind.SIMILAR_TO, score=score)
            )
            self.add_edge(
                Edge(from_work=other_id, to_work=work_id, kind=EdgeKind.SIMILAR_TO, score=score)
            )

    def _citation_neighbors(
        self,
        seed: Work,
        subcategory: str,
        as_of: date | None,
        blocked: frozenset[UUID],
        _k: int,
    ) -> tuple[Neighbor, ...]:
        """Walk cites edges.

        Args:
            seed: Center work.
            subcategory: Filter.
            as_of: Date bound.
            blocked: Dropped ids.
            _k: Unused.

        Returns:
            Citation neighbors.
        """
        rows: list[Neighbor] = []
        for edge in self.edges(EdgeKind.CITES):
            neighbor = _edge_neighbor(edge, seed.id, self._works)
            if neighbor is None:
                continue
            if _visible(neighbor.work, seed.id, subcategory, as_of, blocked):
                rows.append(neighbor)
        return tuple(rows)

    def _content_neighbors(
        self,
        seed: Work,
        subcategory: str,
        as_of: date | None,
        blocked: frozenset[UUID],
        k: int,
    ) -> tuple[Neighbor, ...]:
        """Walk similar_to edges.

        Args:
            seed: Center work.
            subcategory: Filter.
            as_of: Date bound.
            blocked: Dropped ids.
            k: Max rows.

        Returns:
            Content neighbors.
        """
        rows: list[Neighbor] = []
        for edge in self.edges(EdgeKind.SIMILAR_TO):
            neighbor = _edge_neighbor(edge, seed.id, self._works)
            if neighbor is None:
                continue
            if _visible(neighbor.work, seed.id, subcategory, as_of, blocked):
                rows.append(neighbor)
        ranked = sorted(rows, key=lambda item: item.score or 0.0, reverse=True)
        return tuple(ranked[:k])

    def _union_neighbors(
        self,
        seed: Work,
        subcategory: str,
        as_of: date | None,
        blocked: frozenset[UUID],
        k: int,
    ) -> tuple[Neighbor, ...]:
        """Return citation plus content neighbors.

        Args:
            seed: Center work.
            subcategory: Filter.
            as_of: Date bound.
            blocked: Dropped ids.
            k: Content cap.

        Returns:
            Combined neighbors.
        """
        citation = self._citation_neighbors(seed, subcategory, as_of, blocked, k)
        content = self._content_neighbors(seed, subcategory, as_of, blocked, k)
        return citation + content


def _row_for(identity: Identity, index: dict[tuple[str, str], UUID]) -> BatchCheckRow:
    """Build one batch-check row.

    Args:
        identity: Query identity.
        index: Identity map.

    Returns:
        Known or unknown row.
    """
    work_id = index.get((identity.kind.value, identity.value))
    return BatchCheckRow(identity=identity, known=work_id is not None, work_id=work_id)


def _visible(
    work: Work,
    seed_id: UUID,
    subcategory: str,
    as_of: date | None,
    blocked: frozenset[UUID],
) -> bool:
    """Return whether a neighbor passes filters.

    Args:
        work: Candidate neighbor.
        seed_id: Seed to exclude.
        subcategory: Required subcategory.
        as_of: Last allowed publication date. Works on the next day are future.
        blocked: Extra exclusions.

    Returns:
        True when the neighbor should be returned.
    """
    if work.id == seed_id or work.id in blocked:
        return False
    if not has_subcategory(work, subcategory):
        return False
    return as_of is None or work.published_on <= as_of


def _edge_neighbor(edge: Edge, seed_id: UUID, works: dict[UUID, Work]) -> Neighbor | None:
    """Map an edge onto a Neighbor relative to the seed.

    Args:
        edge: Stored edge.
        seed_id: Center id.
        works: Work index.

    Returns:
        Neighbor or None when the edge does not touch the seed.
    """
    mapping = {
        edge.from_work: (edge.to_work, NeighborDirection.OUT),
        edge.to_work: (edge.from_work, NeighborDirection.IN),
    }
    if seed_id not in mapping:
        return None
    other_id, direction = mapping[seed_id]
    other = works.get(other_id)
    if other is None:
        return None
    return Neighbor(work=other, edge_kind=edge.kind, direction=direction, score=edge.score)


def scored_neighbors(
    work_id: UUID,
    source: tuple[float, ...],
    embeddings: dict[UUID, tuple[float, ...]],
    models: dict[UUID, str] | None = None,
    model_id: str | None = None,
) -> list[tuple[UUID, float]]:
    """Rank other embeddings by cosine similarity.

    Args:
        work_id: Query work.
        source: Query vector.
        embeddings: All vectors.
        models: Optional work id to embedding model id.
        model_id: When set, only compare vectors from this model.

    Returns:
        (id, score) pairs, highest first.
    """
    scored: list[tuple[UUID, float]] = []
    for other_id, vector in embeddings.items():
        if other_id == work_id:
            continue
        if model_id is not None and models is not None and models.get(other_id) != model_id:
            continue
        if len(vector) != len(source):
            continue
        scored.append((other_id, cosine(source, vector)))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored
