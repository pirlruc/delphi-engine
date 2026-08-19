"""Epimetheus CLI: run one hindcast against a leak-proof fixture graph."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from uuid import uuid4

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

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Run the fixture hindcast and write an EvalRun JSON artifact.

    Args:
        argv: Optional CLI args.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(description="Epimetheus hindcast")
    parser.add_argument("--output", type=Path, default=Path("evalrun.json"))
    args = parser.parse_args(argv)
    run = run_hindcast(*_fixture_trial())
    args.output.write_text(run.model_dump_json(indent=2), encoding="utf-8")
    return 0


def _fixture_trial() -> tuple[
    Work,
    Work,
    tuple[Work, ...],
    tuple[Edge, ...],
    tuple[Neighbor, ...],
    str,
    PathKind,
]:
    """Build the QR 2014 vs 2020 color-watermark hindcast.

    Returns:
        Arguments for ``run_hindcast``.
    """
    seed = _work("QR 2014", date(2014, 6, 1))
    held = _work("Color QR watermarks", date(2020, 2, 1))
    prior = _work("QR 2012", date(2012, 1, 1))
    works = (seed, held, prior)
    edges = (Edge(from_work=seed.id, to_work=prior.id, kind=EdgeKind.CITES),)
    neighbors = (
        Neighbor(work=prior, edge_kind=EdgeKind.CITES, direction=NeighborDirection.OUT),
        Neighbor(
            work=held,
            edge_kind=EdgeKind.SIMILAR_TO,
            direction=NeighborDirection.OUT,
            score=0.99,
        ),
    )
    return seed, held, works, edges, neighbors, "two_d_codes", PathKind.RESEARCH_PATH


def _work(title: str, published: date) -> Work:
    """Build a 2D-code paper.

    Args:
        title: Title.
        published: Publication date.

    Returns:
        Work record.
    """
    return Work(
        id=uuid4(),
        kind=WorkKind.PAPER,
        title=title,
        abstract=title,
        published_on=published,
        categories=(
            Category(
                scheme=CategoryScheme.OPENALEX_TOPIC,
                code="two-d",
                label="2D",
                subcategory=SubcategoryId.TWO_D_CODES,
            ),
        ),
    )
