"""Prometheus leak-proof generation tests."""

from datetime import date
from uuid import uuid4

import pytest
from delphi_contracts.category import Category
from delphi_contracts.enums import (
    CategoryScheme,
    EdgeKind,
    NeighborDirection,
    NeighborhoodMode,
    PathKind,
    SubcategoryId,
    WorkKind,
)
from delphi_contracts.neighborhood import Neighbor, Neighborhood
from delphi_contracts.paths import ContextLeakError, MaskedContext
from delphi_contracts.work import Work

from delphi_prometheus import PathGenerator
from delphi_prometheus.generate import assert_no_leak


def _work(title: str, published: date) -> Work:
    return Work(
        id=uuid4(),
        kind=WorkKind.PAPER,
        title=title,
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


def _context(
    seed: Work, neighbors: tuple[Neighbor, ...], mask_on: date, held_out=()
) -> MaskedContext:
    return MaskedContext(
        seed=seed,
        mask_on=mask_on,
        held_out_ids=tuple(held_out),
        neighborhood=Neighborhood(seed=seed, mode=NeighborhoodMode.UNION, neighbors=neighbors),
        subcategory="two_d_codes",
        kind=PathKind.RESEARCH_PATH,
    )


def test_generate_from_clean_context() -> None:
    seed = _work("QR 2014", date(2014, 6, 1))
    neighbor = _work("QR 2012", date(2012, 1, 1))
    context = _context(
        seed,
        (
            Neighbor(
                work=neighbor,
                edge_kind=EdgeKind.CITES,
                direction=NeighborDirection.OUT,
            ),
        ),
        date(2016, 1, 1),
    )
    proposals = PathGenerator().generate(context)
    assert proposals[0].kind is PathKind.RESEARCH_PATH
    assert proposals[0].cited_work_ids


def test_leak_future_and_held_out() -> None:
    seed = _work("QR 2014", date(2014, 6, 1))
    future = _work("QR 2018", date(2018, 1, 1))
    context = _context(
        seed,
        (
            Neighbor(
                work=future,
                edge_kind=EdgeKind.SIMILAR_TO,
                direction=NeighborDirection.OUT,
                score=0.9,
            ),
        ),
        date(2016, 1, 1),
        held_out=(future.id,),
    )
    with pytest.raises(ContextLeakError):
        PathGenerator().generate(context)


def test_same_day_neighbor_is_a_leak() -> None:
    seed = _work("QR 2014", date(2014, 6, 1))
    sibling = _work("same day", date(2016, 3, 1))
    context = _context(
        seed,
        (
            Neighbor(
                work=sibling,
                edge_kind=EdgeKind.SIMILAR_TO,
                direction=NeighborDirection.OUT,
                score=0.4,
            ),
        ),
        date(2016, 3, 1),
    )
    with pytest.raises(ContextLeakError):
        assert_no_leak(context)


def test_assert_no_leak_clean() -> None:
    seed = _work("seed", date(2014, 1, 1))
    assert_no_leak(_context(seed, (), date(2016, 1, 1)))


def test_held_out_absent_from_neighbors_is_not_a_leak() -> None:
    seed = _work("QR 2014", date(2014, 6, 1))
    held = _work("Color QR watermarks", date(2020, 2, 1))
    context = _context(seed, (), date(2016, 1, 1), held_out=(held.id,))
    proposals = PathGenerator().generate(context)
    assert proposals[0].kind is PathKind.RESEARCH_PATH


def test_proposal_fallbacks() -> None:
    from delphi_prometheus.generate import _proposal

    proposal = _proposal({"kind": "nope", "cited_work_ids": "bad"}, PathKind.PATENT_WHITESPACE)
    assert proposal.kind is PathKind.PATENT_WHITESPACE
    assert proposal.claims == ("Next step.",)
    kept = uuid4()
    filtered = _proposal(
        {"cited_work_ids": [str(kept), str(uuid4())]},
        PathKind.RESEARCH_PATH,
        {kept},
    )
    assert filtered.cited_work_ids == (kept,)
