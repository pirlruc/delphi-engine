"""Leak-proof temporal masks for both graphs."""

from datetime import date
from uuid import UUID

from delphi_contracts.enums import NeighborhoodMode
from delphi_contracts.mask import citation_descendants, dropped_ids
from delphi_contracts.neighborhood import Neighbor, Neighborhood
from delphi_contracts.paths import MaskedContext, PathKind
from delphi_contracts.work import Work

__all__ = ["citation_descendants", "dropped_ids", "masked_context"]


def masked_context(
    seed: Work,
    neighbors: tuple[Neighbor, ...],
    held_out_id: UUID,
    cut: date,
    dropped: frozenset[UUID],
    kind: PathKind,
    subcategory: str,
) -> MaskedContext:
    """Filter neighbors and wrap a MaskedContext.

    Args:
        seed: Past seed work.
        neighbors: Unmasked neighborhood.
        held_out_id: Hidden work.
        cut: Mask date.
        dropped: Ids from dropped_ids.
        kind: Query kind.
        subcategory: Filter.

    Returns:
        Context with future/held-out neighbors removed.
    """
    kept = tuple(
        neighbor
        for neighbor in neighbors
        if neighbor.work.id not in dropped and neighbor.work.published_on < cut
    )
    return MaskedContext(
        seed=seed,
        mask_on=cut,
        held_out_ids=(held_out_id,),
        neighborhood=Neighborhood(
            seed=seed, mode=NeighborhoodMode.UNION, neighbors=kept
        ),
        subcategory=subcategory,
        kind=kind,
    )
