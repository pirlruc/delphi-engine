"""Structural catalog writer used by ingest and embed."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from delphi_contracts.graph import Edge
from delphi_contracts.work import Work

__all__ = ["CatalogWriter"]


class CatalogWriter(Protocol):
    """Subset of Delphi's catalog used by Daedalus."""

    def upsert_work(self, work: Work) -> Work:
        """Store a work.

        Args:
            work: Record to upsert.

        Returns:
            Stored work.
        """

    def add_edge(self, edge: Edge) -> None:
        """Store an edge.

        Args:
            edge: cites or similar_to.
        """

    def put_embedding(self, work_id: UUID, vector: tuple[float, ...], model_id: str) -> None:
        """Store a vector.

        Args:
            work_id: Work UUID.
            vector: Embedding.
            model_id: Model id.
        """

    def rebuild_similar_to(self, work_id: UUID, k: int = 8) -> None:
        """Refresh content-graph edges.

        Args:
            work_id: Work to refresh.
            k: Neighbor cap.
        """

    def rebuild_all_similar_to(self, k: int = 8) -> None:
        """Recompute every similar_to edge after bulk embedding.

        Args:
            k: Neighbor cap.
        """
