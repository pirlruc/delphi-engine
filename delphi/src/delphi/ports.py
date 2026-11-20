"""Injectable ports so Delphi does not import sibling packages."""

from __future__ import annotations

from typing import Protocol

from delphi_contracts.extraction import Extraction
from delphi_contracts.paths import MaskedContext, PathProposal
from delphi_contracts.work import Work

__all__ = ["Embedder", "Extractor", "Generator"]


class Extractor(Protocol):
    """PDF extraction implemented by Daedalus."""

    def extract(self, pdf_bytes: bytes, filename: str) -> Extraction:
        """Turn PDF bytes into structured fields.

        Args:
            pdf_bytes: Raw PDF.
            filename: Original name.

        Returns:
            Extraction record.
        """


class Embedder(Protocol):
    """Content-graph embeddings implemented by Daedalus."""

    def embed_and_link(self, work: Work, text: str) -> None:
        """Embed text and refresh similar_to edges.

        Args:
            work: Catalog work.
            text: Title+abstract or extracted body.
        """


class Generator(Protocol):
    """Path generator implemented by Prometheus."""

    def generate(self, context: MaskedContext) -> tuple[PathProposal, ...]:
        """Propose paths from a masked neighborhood.

        Args:
            context: Past-only context.

        Returns:
            Ranked proposals.
        """
