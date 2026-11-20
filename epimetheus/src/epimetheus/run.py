"""Run one hindcast trial: mask, generate, score."""

from __future__ import annotations

from delphi_contracts.eval_run import EvalRun
from delphi_contracts.graph import Edge
from delphi_contracts.neighborhood import Neighbor
from delphi_contracts.paths import PathKind
from delphi_contracts.work import Work
from delphi_prometheus import PathGenerator

from epimetheus.mask import dropped_ids, masked_context
from epimetheus.score import score_proposal

__all__ = ["run_hindcast"]


def run_hindcast(
    seed: Work,
    held_out: Work,
    works: tuple[Work, ...],
    edges: tuple[Edge, ...],
    neighbors: tuple[Neighbor, ...],
    subcategory: str,
    kind: PathKind = PathKind.RESEARCH_PATH,
    generator: PathGenerator | None = None,
) -> EvalRun:
    """Mask both graphs, generate, and score against the held-out work.

    Args:
        seed: Past seed.
        held_out: Hidden later work.
        works: Full catalog works.
        edges: Full catalog edges.
        neighbors: Unmasked neighborhood of the seed.
        subcategory: Filter.
        kind: Query kind.
        generator: Prometheus generator. Defaults to Fake LLM.

    Returns:
        EvalRun artifact.
    """
    cut = held_out.published_on
    dropped = dropped_ids(works, edges, held_out.id, cut)
    context = masked_context(seed, neighbors, held_out.id, cut, dropped, kind, subcategory)
    proposals = (generator or PathGenerator()).generate(context)
    if not proposals:
        raise ValueError("generator returned no proposals")
    return score_proposal(proposals[0], held_out, seed.id, subcategory)
