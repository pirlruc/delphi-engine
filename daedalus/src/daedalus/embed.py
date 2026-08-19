"""Content-graph embeddings against other papers."""

from __future__ import annotations

from delphi_contracts.llm import EmbedRequest, LlmProvider, build_provider
from delphi_contracts.work import Work

from daedalus.ports import CatalogWriter

__all__ = ["HashEmbedder"]


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

    def embed_and_link(self, work: Work, text: str) -> None:
        """Embed text for a work and rebuild its content-graph edges.

        Args:
            work: Catalog work.
            text: Title+abstract or extracted body.
        """
        response = self._llm.embed(EmbedRequest(text=text))
        self._catalog.put_embedding(work.id, response.vector, response.model)
        self._catalog.rebuild_similar_to(work.id)
