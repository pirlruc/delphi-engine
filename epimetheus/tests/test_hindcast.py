"""Hindcast mask and scoring tests."""

import json
from datetime import date
from pathlib import Path
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
from delphi_contracts.graph import Edge
from delphi_contracts.neighborhood import Neighbor, Neighborhood
from delphi_contracts.paths import ContextLeakError, MaskedContext, PathProposal
from delphi_contracts.work import Work
from delphi_prometheus import PathGenerator

from epimetheus.cli import main
from epimetheus.mask import citation_descendants, dropped_ids, masked_context
from epimetheus.run import run_hindcast
from epimetheus.score import score_proposal


def _work(title: str, published: date, work_id=None) -> Work:
    return Work(
        id=work_id or uuid4(),
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


def test_leak_fixtures_future_descendant_similar_and_same_year() -> None:
    seed = _work("QR 2014", date(2014, 6, 1))
    held = _work("QR 2016-03", date(2016, 3, 1))
    future = _work("QR 2018", date(2018, 1, 1))
    same_year_after = _work("QR 2016-11", date(2016, 11, 1))
    descendant = _work("Cites held-out", date(2016, 4, 1))
    edges = (
        Edge(from_work=descendant.id, to_work=held.id, kind=EdgeKind.CITES),
        Edge(from_work=future.id, to_work=seed.id, kind=EdgeKind.CITES),
        Edge(from_work=seed.id, to_work=held.id, kind=EdgeKind.SIMILAR_TO, score=0.8),
        Edge(from_work=seed.id, to_work=same_year_after.id, kind=EdgeKind.SIMILAR_TO, score=0.7),
    )
    works = (seed, held, future, same_year_after, descendant)
    dropped = dropped_ids(works, edges, held.id, held.published_on)
    assert held.id in dropped
    assert future.id in dropped
    assert descendant.id in dropped
    assert same_year_after.id in dropped
    assert seed.id not in dropped
    sibling = _work("Same day as held-out", date(2016, 3, 1))
    same_day = dropped_ids((seed, held, sibling), edges, held.id, held.published_on)
    assert sibling.id in same_day
    assert held.id in citation_descendants(held.id, edges) or descendant.id in citation_descendants(
        held.id, edges
    )


def test_masked_context_drops_later_content_neighbor() -> None:
    seed = _work("seed", date(2014, 1, 1))
    later = _work("later", date(2019, 1, 1))
    neighbor = Neighbor(
        work=later,
        edge_kind=EdgeKind.SIMILAR_TO,
        direction=NeighborDirection.OUT,
        score=0.9,
    )
    dropped = frozenset({later.id})
    context = masked_context(
        seed,
        (neighbor,),
        later.id,
        date(2016, 1, 1),
        dropped,
        PathKind.RESEARCH_PATH,
        "two_d_codes",
    )
    assert context.neighborhood.neighbors == ()


def test_run_hindcast_and_score(tmp_path: Path) -> None:
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
    run = run_hindcast(seed, held, works, edges, neighbors, "two_d_codes")
    assert run.held_out_id == held.id
    assert 1 <= run.scores.novelty <= 5
    proposal = PathProposal(
        kind=PathKind.RESEARCH_PATH,
        title="Color QR watermarks",
        claims=("Extend QR.",),
        rationale="test",
        rank=1,
    )
    scored = score_proposal(proposal, held, seed.id, "two_d_codes")
    assert scored.scores.embedding_similarity >= 0.0
    output = tmp_path / "evalrun.json"
    assert main(["--output", str(output)]) == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["kind"] == "research_path"
    assert artifact["scores"]["novelty"] >= 1
    slice_json = tmp_path / "slice.json"
    slice_json.write_text(
        json.dumps({
            "works": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "kind": "paper",
                    "title": "Early",
                    "abstract": "qr",
                    "published_on": "2014-01-01",
                    "subcategory": "two_d_codes",
                    "cites": [],
                },
                {
                    "id": "88888888-8888-8888-8888-888888888888",
                    "kind": "paper",
                    "title": "Late",
                    "abstract": "qr watermark",
                    "published_on": "2020-01-01",
                    "subcategory": "two_d_codes",
                    "cites": ["11111111-1111-1111-1111-111111111111"],
                },
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "kind": "paper",
                    "title": "Cites seed later",
                    "abstract": "qr",
                    "published_on": "2015-01-01",
                    "subcategory": "two_d_codes",
                    "cites": ["11111111-1111-1111-1111-111111111111"],
                },
                {
                    "id": "33333333-3333-3333-3333-333333333333",
                    "kind": "paper",
                    "title": "Same day a",
                    "published_on": "2016-01-01",
                    "subcategory": "steganography",
                    "cites": ["11111111-1111-1111-1111-111111111111"],
                },
                {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "kind": "paper",
                    "title": "Same day b",
                    "published_on": "2016-01-01",
                    "subcategory": "steganography",
                    "cites": [],
                },
            ]
        })
    )
    summary_path = tmp_path / "summary.json"
    assert main(["--works-json", str(slice_json), "--output", str(summary_path)]) == 0
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["trial_count"] == 1
    assert summary["mean_novelty"] >= 1
    one = tmp_path / "one.json"
    one.write_text(
        json.dumps({
            "works": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "kind": "paper",
                    "title": "Only",
                    "published_on": "2014-01-01",
                    "subcategory": "two_d_codes",
                    "cites": [],
                }
            ]
        })
    )
    empty_path = tmp_path / "empty.json"
    assert main(["--works-json", str(one), "--output", str(empty_path)]) == 0
    assert json.loads(empty_path.read_text(encoding="utf-8"))["trial_count"] == 0


def test_run_hindcast_fails_if_seed_neighborhood_unmasked() -> None:
    seed = _work("seed", date(2014, 1, 1))
    held = _work("held", date(2016, 1, 1))
    neighbors = (
        Neighbor(
            work=held,
            edge_kind=EdgeKind.SIMILAR_TO,
            direction=NeighborDirection.OUT,
            score=0.9,
        ),
    )
    leaked = MaskedContext(
        seed=seed,
        mask_on=date(2015, 1, 1),
        held_out_ids=(held.id,),
        neighborhood=Neighborhood(
            seed=seed,
            mode=NeighborhoodMode.UNION,
            neighbors=neighbors,
        ),
        subcategory="two_d_codes",
        kind=PathKind.RESEARCH_PATH,
    )
    with pytest.raises(ContextLeakError):
        PathGenerator().generate(leaked)


def test_citation_descendant_cycle_safe() -> None:
    a = uuid4()
    b = uuid4()
    edges = (
        Edge(from_work=a, to_work=b, kind=EdgeKind.CITES),
        Edge(from_work=b, to_work=a, kind=EdgeKind.CITES),
    )
    result = citation_descendants(a, edges)
    assert b in result
    assert a in result
