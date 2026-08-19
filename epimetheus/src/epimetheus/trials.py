"""Build hindcast trials from a Daedalus-shaped works JSON file."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from delphi_contracts.category import Category
from delphi_contracts.enums import (
    CategoryScheme,
    EdgeKind,
    NeighborDirection,
    PathKind,
    SubcategoryId,
    WorkKind,
)
from delphi_contracts.graph import Edge
from delphi_contracts.neighborhood import Neighbor
from delphi_contracts.work import Work

from epimetheus.run import run_hindcast

__all__ = ["summarize_runs", "trials_from_payload"]


def trials_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Run one earliest-vs-latest hindcast per subcategory.

    Args:
        payload: ``{"works": [...]}`` fixture JSON.

    Returns:
        EvalRun dicts plus trial metadata.
    """
    works, edges, by_sub = _load(payload)
    results: list[dict[str, Any]] = []
    for subcategory, group in sorted(by_sub.items()):
        papers = sorted(group, key=lambda work: work.published_on)
        if len(papers) < 2:
            continue
        seed, held = papers[0], papers[-1]
        if held.published_on <= seed.published_on:
            continue
        neighbors = _neighbors(seed, group, edges)
        run = run_hindcast(seed, held, works, edges, neighbors, subcategory, PathKind.RESEARCH_PATH)
        dumped = run.model_dump(mode="json")
        dumped["seed_title"] = seed.title
        dumped["held_out_title"] = held.title
        results.append(dumped)
    return results


def summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate trial count and mean scores.

    Args:
        runs: EvalRun dicts.

    Returns:
        Summary object for PROTO-007.
    """
    count = len(runs)
    if count == 0:
        return {
            "trial_count": 0,
            "mean_novelty": 0.0,
            "mean_relevance": 0.0,
            "mean_accuracy": 0.0,
            "mean_embedding_similarity": 0.0,
            "runs": [],
        }
    novelty = sum(float(run["scores"]["novelty"]) for run in runs) / count
    relevance = sum(float(run["scores"]["relevance"]) for run in runs) / count
    accuracy = sum(float(run["scores"]["accuracy"]) for run in runs) / count
    similarity = sum(float(run["scores"]["embedding_similarity"]) for run in runs) / count
    return {
        "trial_count": count,
        "mean_novelty": novelty,
        "mean_relevance": relevance,
        "mean_accuracy": accuracy,
        "mean_embedding_similarity": similarity,
        "runs": runs,
    }


def _load(
    payload: dict[str, Any],
) -> tuple[tuple[Work, ...], tuple[Edge, ...], dict[str, list[Work]]]:
    """Parse works and cites.

    Args:
        payload: Fixture JSON.

    Returns:
        Works, cites edges, works grouped by subcategory.
    """
    records = payload["works"]
    works: list[Work] = []
    edges: list[Edge] = []
    by_sub: dict[str, list[Work]] = {}
    for record in records:
        work = _work(record)
        works.append(work)
        subcategory = str(record["subcategory"])
        by_sub.setdefault(subcategory, []).append(work)
        for target in record.get("cites", []):
            edges.append(Edge(from_work=work.id, to_work=UUID(str(target)), kind=EdgeKind.CITES))
    return tuple(works), tuple(edges), by_sub


def _work(record: dict[str, Any]) -> Work:
    """Build a Work from a fixture row.

    Args:
        record: Fixture dict.

    Returns:
        Work.
    """
    subcategory = str(record["subcategory"])
    parsed = SubcategoryId(subcategory)
    scheme = CategoryScheme.CPC if record["kind"] == "patent" else CategoryScheme.OPENALEX_TOPIC
    return Work(
        id=UUID(str(record["id"])),
        kind=WorkKind(str(record["kind"])),
        title=str(record["title"]),
        abstract=str(record.get("abstract", "")),
        published_on=date.fromisoformat(str(record["published_on"])),
        categories=(
            Category(
                scheme=scheme,
                code=subcategory,
                label=subcategory.replace("_", " "),
                subcategory=parsed,
            ),
        ),
    )


def _neighbors(seed: Work, group: list[Work], edges: tuple[Edge, ...]) -> tuple[Neighbor, ...]:
    """Citation neighbors plus similar_to to every other work in the subcategory.

    Args:
        seed: Past seed.
        group: Works in the same subcategory.
        edges: Catalog cites.

    Returns:
        Unmasked neighborhood including the later held-out similar_to edge.
    """
    by_id = {work.id: work for work in group}
    rows: list[Neighbor] = []
    for edge in edges:
        other_id = None
        direction = NeighborDirection.OUT
        if edge.from_work == seed.id:
            other_id = edge.to_work
        elif edge.to_work == seed.id:
            other_id = edge.from_work
            direction = NeighborDirection.IN
        other = by_id.get(other_id) if other_id is not None else None
        if other is not None:
            rows.append(Neighbor(work=other, edge_kind=EdgeKind.CITES, direction=direction))
    for work in group:
        if work.id == seed.id:
            continue
        rows.append(
            Neighbor(
                work=work,
                edge_kind=EdgeKind.SIMILAR_TO,
                direction=NeighborDirection.OUT,
                score=0.5,
            )
        )
    return tuple(rows)
