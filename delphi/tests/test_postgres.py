"""Postgres catalog tests (SYS-002)."""

import os
from datetime import date
from uuid import uuid4

import pytest
from delphi_contracts.batch import BatchCheckRequest
from delphi_contracts.category import Category
from delphi_contracts.enums import (
    CategoryScheme,
    EdgeKind,
    IdentityKind,
    NeighborhoodMode,
    SubcategoryId,
    WorkKind,
)
from delphi_contracts.extraction import Extraction
from delphi_contracts.graph import Edge
from delphi_contracts.identity import Identity
from delphi_contracts.llm import hash_embed
from delphi_contracts.work import Work

from delphi.catalog import MemoryCatalog
from delphi.postgres import PostgresCatalog, catalog_from_url

_DSN = os.environ.get(
    "DELPHI_TEST_DATABASE_URL",
    "postgresql://delphi:delphi@127.0.0.1:5432/delphi_test",
)


def _available() -> bool:
    try:
        catalog = PostgresCatalog(_DSN, reset=True)
        catalog.close()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(not _available(), reason="postgres unavailable")


def _category() -> Category:
    return Category(
        scheme=CategoryScheme.OPENALEX_TOPIC,
        code="two-d",
        label="2D codes",
        subcategory=SubcategoryId.TWO_D_CODES,
    )


def _work(title: str, published: date, doi: str | None = None) -> Work:
    ident = doi or title
    return Work(
        id=uuid4(),
        kind=WorkKind.PAPER,
        title=title,
        abstract=title,
        published_on=published,
        identities=(Identity(kind=IdentityKind.DOI, value=ident),),
        categories=(_category(),),
    )


@pytest.fixture
def catalog() -> PostgresCatalog:
    store = PostgresCatalog(_DSN, reset=True)
    yield store
    store.close()


def test_catalog_from_url_defaults_to_memory() -> None:
    assert isinstance(catalog_from_url(None), MemoryCatalog)
    pg = catalog_from_url(_DSN)
    assert isinstance(pg, PostgresCatalog)
    pg.close()  # type: ignore[union-attr]


def test_postgres_works_edges_embeddings_and_neighborhood(catalog: PostgresCatalog) -> None:
    seed = _work("QR 2014", date(2014, 6, 1), "10.1/a")
    cited = _work("QR 2012", date(2012, 1, 1), "10.1/b")
    later = _work("QR 2018", date(2018, 1, 1), "10.1/c")
    for work in (seed, cited, later):
        catalog.upsert_work(work)
        catalog.put_embedding(work.id, hash_embed(work.title), "fake")
    catalog.add_edge(Edge(from_work=seed.id, to_work=cited.id, kind=EdgeKind.CITES))
    catalog.add_edge(Edge(from_work=seed.id, to_work=seed.id, kind=EdgeKind.CITES))
    catalog.rebuild_similar_to(seed.id, k=8)
    catalog.upsert_work(seed)
    assert catalog.get_work(seed.id) is not None
    assert catalog.get_work(uuid4()) is None
    assert catalog.get_embedding(seed.id) is not None
    assert catalog.get_embedding(uuid4()) is None
    response = catalog.batch_check(
        BatchCheckRequest(
            identities=(
                Identity(kind=IdentityKind.DOI, value="10.1/a"),
                Identity(kind=IdentityKind.DOI, value="10.1/missing"),
            )
        )
    )
    assert response.rows[0].known is True
    assert response.rows[1].known is False
    citation = catalog.neighborhood(seed.id, NeighborhoodMode.CITATION, "two_d_codes")
    assert {item.work.id for item in citation.neighbors} == {cited.id}
    content = catalog.neighborhood(
        seed.id, NeighborhoodMode.CONTENT, "two_d_codes", as_of=date(2016, 1, 1)
    )
    assert later.id not in {item.work.id for item in content.neighbors}
    assert catalog.edges(EdgeKind.CITES)
    assert catalog.list_works()
    missing = _work("no vec", date(2011, 1, 1), "10.1/none")
    catalog.upsert_work(missing)
    catalog.rebuild_similar_to(missing.id)
    catalog.rebuild_all_similar_to(k=8)
    assert catalog.edges(EdgeKind.SIMILAR_TO)


def test_postgres_extractions_and_empty_vector(catalog: PostgresCatalog) -> None:
    extraction = Extraction(id=uuid4(), content_hash="a" * 64, title="PDF", body_text="x")
    catalog.put_extraction(extraction)
    catalog.put_extraction(extraction)
    assert catalog.get_extraction(extraction.id) is not None
    assert catalog.get_extraction(uuid4()) is None
    assert catalog.get_extraction_by_hash("a" * 64) is not None
    assert catalog.get_extraction_by_hash("z" * 64) is None
    assert catalog.edges() == ()
    from delphi.postgres import _vector

    assert _vector("nope") == ()
