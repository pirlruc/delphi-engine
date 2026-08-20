"""Hindcast drop-set helpers shared by Delphi generate and Epimetheus."""

from collections import defaultdict, deque
from datetime import date
from uuid import UUID

from delphi_contracts.enums import EdgeKind
from delphi_contracts.graph import Edge
from delphi_contracts.work import Work

__all__ = ["citation_descendants", "dropped_ids"]


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

    Same-calendar-day siblings of the held-out work are treated as future
    (``published_on >= cut``) so a co-published paper cannot leak into the
    generator prompt.

    Args:
        works: Catalog works.
        edges: Catalog edges.
        held_out_id: Hidden work.
        cut: Held-out publication date.

    Returns:
        Held-out id, contemporaneous-or-later works, and citation descendants.
    """
    later = {work.id for work in works if work.published_on >= cut}
    descendants = citation_descendants(held_out_id, edges)
    return frozenset({held_out_id}) | frozenset(later) | descendants
