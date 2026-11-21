"""Graph edges stored beside works."""

from typing import Annotated
from uuid import UUID

from annotated_types import Ge, Le
from pydantic import BaseModel, ConfigDict

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
    score: Annotated[float | None, Ge(0.0), Le(1.0)] = None
