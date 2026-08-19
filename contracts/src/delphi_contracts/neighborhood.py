"""Neighborhood query results."""

from pydantic import BaseModel, ConfigDict, Field

from delphi_contracts.enums import EdgeKind, NeighborDirection, NeighborhoodMode
from delphi_contracts.work import Work

__all__ = ["Neighbor", "Neighborhood", "NeighborhoodMode"]


class Neighbor(BaseModel):
    """One dated neighbor tagged by edge kind.

    Attributes:
        work: Neighbor catalog record.
        edge_kind: cites or similar_to.
        direction: in or out relative to the seed.
        score: Similarity score when edge_kind is similar_to.
    """

    model_config = ConfigDict(frozen=True)

    work: Work
    edge_kind: EdgeKind
    direction: NeighborDirection
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class Neighborhood(BaseModel):
    """Citation and/or content neighbors of a seed work.

    Attributes:
        seed: Center work.
        mode: Requested graph mode.
        neighbors: Tagged neighbor rows.
    """

    model_config = ConfigDict(frozen=True)

    seed: Work
    mode: NeighborhoodMode
    neighbors: tuple[Neighbor, ...] = ()
