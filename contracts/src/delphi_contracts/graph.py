"""Graph edges stored beside works."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from delphi_contracts.enums import EdgeKind

__all__ = ["Edge", "EdgeKind"]


class Edge(BaseModel):
    """A directed catalog edge.

    Attributes:
        from_work: Source work id.
        to_work: Target work id.
        kind: cites or similar_to.
        score: Similarity score for similar_to; None for cites.
    """

    model_config = ConfigDict(frozen=True)

    from_work: UUID
    to_work: UUID
    kind: EdgeKind
    score: float | None = Field(default=None, ge=0.0, le=1.0)
