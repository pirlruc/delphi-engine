"""Path generation request, context, and proposals."""

from datetime import date
from typing import Annotated, Self
from uuid import UUID

from annotated_types import Ge, MinLen
from pydantic import BaseModel, ConfigDict, model_validator

from delphi_contracts.enums import PathKind
from delphi_contracts.neighborhood import Neighborhood
from delphi_contracts.work import Work

__all__ = [
    "ContextLeakError",
    "MaskedContext",
    "PathKind",
    "PathProposal",
    "PathRequest",
]


class ContextLeakError(ValueError):
    """Raised when a MaskedContext contains a future or held-out work."""


class PathRequest(BaseModel):
    """Generate a research path or patent whitespace.

    Attributes:
        kind: research_path or patent_whitespace.
        subcategory: Required SYS-009 filter.
        seed_work_id: Catalog work to expand from.
        extraction_id: Uploaded extraction to expand from when not yet a work.
        as_of: Optional temporal bound (inclusive).
    """

    model_config = ConfigDict(frozen=True)

    kind: PathKind
    subcategory: Annotated[str, MinLen(1)]
    seed_work_id: UUID | None = None
    extraction_id: UUID | None = None
    as_of: date | None = None

    @model_validator(mode="after")
    def _require_seed(self) -> Self:
        """Require a catalog work or an extraction as the generate seed.

        Returns:
            This request.

        Raises:
            ValueError: When both seed references are missing.
        """
        if self.seed_work_id is None and self.extraction_id is None:
            raise ValueError("seed_work_id or extraction_id is required")
        return self


class PathProposal(BaseModel):
    """One structured generator output.

    Attributes:
        kind: Same kind as the request.
        title: Short proposal title.
        claims: Concrete next-step claims.
        rationale: Why the neighborhood supports this.
        cited_work_ids: Context work ids the proposal may cite.
        rank: 1 is best.
    """

    model_config = ConfigDict(frozen=True)

    kind: PathKind
    title: Annotated[str, MinLen(1)]
    claims: Annotated[tuple[str, ...], MinLen(1)]
    rationale: Annotated[str, MinLen(1)]
    cited_work_ids: tuple[UUID, ...] = ()
    rank: Annotated[int, Ge(1)]


class MaskedContext(BaseModel):
    """Past-only neighborhood passed to Prometheus.

    Attributes:
        seed: Seed work.
        mask_on: First forbidden publication date. A work on this date is future.
        held_out_ids: Ids that must not appear in neighbors.
        neighborhood: Citation and content neighbors already filtered.
        subcategory: Query filter used to build the neighborhood.
        kind: Intended generation kind.
    """

    model_config = ConfigDict(frozen=True)

    seed: Work
    mask_on: date
    held_out_ids: tuple[UUID, ...] = ()
    neighborhood: Neighborhood
    subcategory: str
    kind: PathKind

    def forbidden_ids(self) -> frozenset[UUID]:
        """Return ids that must not appear in generator context.

        Returns:
            Held-out ids plus any neighbor published on or after the mask date.
        """
        leaked = [
            neighbor.work.id
            for neighbor in self.neighborhood.neighbors
            if neighbor.work.published_on >= self.mask_on
        ]
        present = {
            self.seed.id,
            *(item.work.id for item in self.neighborhood.neighbors),
        }
        held = frozenset(self.held_out_ids) & present
        return held | frozenset(leaked)
