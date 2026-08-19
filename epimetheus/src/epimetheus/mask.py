"""Leak-proof temporal masks for both graphs."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import date
from uuid import UUID

from delphi_contracts.enums import EdgeKind, NeighborhoodMode
from delphi_contracts.graph import Edge
from delphi_contracts.neighborhood import Neighbor, Neighborhood
from delphi_contracts.paths import MaskedContext, PathKind
from delphi_contracts.work import Work

__all__ = ["citation_descendants", "dropped_ids", "masked_context"]


def citation_descendants(held_out_id: UUID, edges: tuple[Edge, ...]) -> frozenset[UUID]:
    """Return works that cite the held-out work, transitively.

    Args:
        held_out_id: Hidden work.
        edges: Catalog cites/similar_to edges.

    Returns:
        Descendant ids (not including the held-out work itself).
    """
    incoming: dict[UUID, list[UUID]] = defaultdict(list)
    for edge in edges:
        if edge.kind is EdgeKind.CITES:
            incoming[edge.to_work].append(edge.from_work)
    seen: set[UUID] = set()
    queue: deque[UUID] = deque(incoming[held_out_id])
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(incoming[current])
    return frozenset(seen)


def dropped_ids(
    works: tuple[Work, ...],
    edges: tuple[Edge, ...],
    held_out_id: UUID,
    cut: date,
) -> frozenset[UUID]:
    """Ids that must not appear in a hindcast context.

    Args:
        works: Catalog works.
        edges: Catalog edges.
        held_out_id: Hidden work.
        cut: Held-out publication date. Later dates are future.

    Returns:
        Held-out id, later works, and citation descendants.
    """
    later = {work.id for work in works if work.published_on > cut}
    descendants = citation_descendants(held_out_id, edges)
    return frozenset({held_out_id}) | frozenset(later) | descendants


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
        if neighbor.work.id not in dropped and neighbor.work.published_on <= cut
    )
    return MaskedContext(
        seed=seed,
        mask_on=cut,
        held_out_ids=(held_out_id,),
        neighborhood=Neighborhood(seed=seed, mode=NeighborhoodMode.UNION, neighbors=kept),
        subcategory=subcategory,
        kind=kind,
    )
