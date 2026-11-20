"""Delphi API tests."""

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
    PathKind,
    SubcategoryId,
    WorkKind,
)
from delphi_contracts.extraction import BibliographyEntry, Extraction
from delphi_contracts.graph import Edge
from delphi_contracts.identity import Identity
from delphi_contracts.llm import hash_embed
from delphi_contracts.paths import ContextLeakError, MaskedContext, PathProposal, PathRequest
from delphi_contracts.work import Work
from fastapi.testclient import TestClient

from delphi.app import AppContainer, create_app
from delphi.catalog import MemoryCatalog, has_subcategory, scored_neighbors
from delphi.services import (
    ConsentError,
    MissingDependencyError,
    attach_bibliography,
    build_masked_context,
    content_hash,
    generate_paths,
    require_consent,
    upload_pdf,
    work_from_extraction,
    work_id_for,
)


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


class _Extractor:
    def __init__(self, extraction: Extraction) -> None:
        self.extraction = extraction
        self.calls = 0

    def extract(self, pdf_bytes: bytes, filename: str) -> Extraction:
        self.calls += 1
        digest = content_hash(pdf_bytes)
        return self.extraction.model_copy(update={"content_hash": digest})


class _Embedder:
    def __init__(self, catalog: MemoryCatalog) -> None:
        self.catalog = catalog

    def embed_and_link(self, work: Work, text: str) -> None:
        self.catalog.put_embedding(work.id, hash_embed(text), "fake-hash")
        self.catalog.rebuild_similar_to(work.id)


class _Generator:
    def generate(self, context: MaskedContext) -> tuple[PathProposal, ...]:
        return (
            PathProposal(
                kind=context.kind,
                title="Next 2D-code experiment",
                claims=("Try color QR watermarks.",),
                rationale="Past-only neighborhood.",
                cited_work_ids=(context.seed.id,),
                rank=1,
            ),
        )


def test_batch_check_mixed_known_unknown() -> None:
    catalog = MemoryCatalog()
    known = _work("QR 2014", date(2014, 6, 1), "10.1/qr")
    catalog.upsert_work(known)
    request = BatchCheckRequest(
        identities=(
            Identity(kind=IdentityKind.DOI, value="10.1/qr"),
            Identity(kind=IdentityKind.DOI, value="10.1/missing"),
        )
    )
    response = catalog.batch_check(request)
    assert response.rows[0].known is True
    assert response.rows[0].work_id == known.id
    assert response.rows[1].known is False


def test_neighborhood_modes_and_filters() -> None:
    catalog = MemoryCatalog()
    seed = _work("QR 2014", date(2014, 6, 1), "10.1/a")
    cited = _work("QR 2012", date(2012, 1, 1), "10.1/b")
    later = _work("QR 2018", date(2018, 1, 1), "10.1/c")
    other_field = Work(
        id=uuid4(),
        kind=WorkKind.PAPER,
        title="Transformers",
        published_on=date(2017, 1, 1),
        identities=(Identity(kind=IdentityKind.DOI, value="10.1/t"),),
        categories=(
            Category(
                scheme=CategoryScheme.OPENALEX_TOPIC,
                code="fm",
                label="FM",
                subcategory=SubcategoryId.TRANSFORMERS_FOUNDATION_MODELS,
            ),
        ),
    )
    for work in (seed, cited, later, other_field):
        catalog.upsert_work(work)
        catalog.put_embedding(work.id, hash_embed(work.title), "fake")
    catalog.add_edge(Edge(from_work=seed.id, to_work=cited.id, kind=EdgeKind.CITES))
    catalog.rebuild_similar_to(seed.id, k=8)
    citation = catalog.neighborhood(seed.id, NeighborhoodMode.CITATION, "two_d_codes")
    assert {item.work.id for item in citation.neighbors} == {cited.id}
    content = catalog.neighborhood(
        seed.id, NeighborhoodMode.CONTENT, "two_d_codes", as_of=date(2016, 1, 1)
    )
    assert later.id not in {item.work.id for item in content.neighbors}
    union = catalog.neighborhood(seed.id, NeighborhoodMode.UNION, "two_d_codes")
    kinds = {item.edge_kind for item in union.neighbors}
    assert EdgeKind.CITES in kinds
    assert other_field.id not in {item.work.id for item in union.neighbors}


def test_rebuild_similar_to_skips_missing_embedding() -> None:
    catalog = MemoryCatalog()
    work = _work("none", date(2015, 1, 1))
    catalog.upsert_work(work)
    catalog.rebuild_similar_to(work.id)
    assert catalog.edges(EdgeKind.SIMILAR_TO) == ()


def test_self_loop_and_duplicate_edges_ignored() -> None:
    catalog = MemoryCatalog()
    work = _work("loop", date(2015, 1, 1))
    catalog.upsert_work(work)
    edge = Edge(from_work=work.id, to_work=work.id, kind=EdgeKind.CITES)
    catalog.add_edge(edge)
    other = _work("other", date(2014, 1, 1))
    catalog.upsert_work(other)
    real = Edge(from_work=work.id, to_work=other.id, kind=EdgeKind.CITES)
    catalog.add_edge(real)
    catalog.add_edge(real)
    updated = real.model_copy(update={"score": 0.4})
    catalog.add_edge(updated)
    assert catalog.edges() == (updated,)


def test_upload_consent_and_bibliography_match() -> None:
    catalog = MemoryCatalog()
    prior = _work("Prior QR", date(2012, 1, 1), "10.1/prior")
    catalog.upsert_work(prior)
    catalog.put_embedding(prior.id, hash_embed("Prior QR"), "fake")
    extraction = Extraction(
        id=uuid4(),
        content_hash="b" * 64,
        title="New QR paper",
        authors=("Ada",),
        keywords=("qr",),
        published_on=date(2015, 1, 1),
        bibliography=(
            BibliographyEntry(
                raw="Prior QR",
                identity=Identity(kind=IdentityKind.DOI, value="10.1/prior"),
            ),
            BibliographyEntry(raw="Unresolved cite"),
        ),
        body_text="Title: New QR paper\nQR barcode data matrix",
    )
    extractor = _Extractor(extraction)
    embedder = _Embedder(catalog)
    stored, neighborhood = upload_pdf(
        catalog,
        b"%PDF-1.4 fake",
        "new.pdf",
        "delphi",
        "two_d_codes",
        extractor,
        embedder,
    )
    assert stored.bibliography[0].matched_work_id == prior.id
    assert stored.bibliography[1].matched_work_id is None
    assert neighborhood.seed.title == "New QR paper"
    assert has_subcategory(neighborhood.seed, "two_d_codes")
    again, _neighborhood = upload_pdf(
        catalog,
        b"%PDF-1.4 fake",
        "new.pdf",
        "delphi",
        "two_d_codes",
        extractor,
        embedder,
    )
    assert again.id == stored.id
    assert extractor.calls == 1
    assert catalog.get_extraction_by_hash("z" * 64) is None


def test_require_consent_rejects_other_destinations() -> None:
    try:
        require_consent("other")
    except ConsentError:
        return
    raise AssertionError("expected ConsentError")


def test_upload_and_generate_http() -> None:
    catalog = MemoryCatalog()
    seed = _work("QR 2014", date(2014, 6, 1), "10.1/seed")
    catalog.upsert_work(seed)
    catalog.put_embedding(seed.id, hash_embed("QR 2014"), "fake")
    extraction = Extraction(
        id=uuid4(),
        content_hash="c" * 64,
        title="Uploaded QR",
        body_text="QR codes",
        published_on=date(2015, 2, 1),
        suggested_categories=(_category(),),
    )
    app = create_app(
        AppContainer(
            catalog=catalog,
            extractor=_Extractor(extraction),
            embedder=_Embedder(catalog),
            generator=_Generator(),
        )
    )
    client = TestClient(app)
    mixed = client.post(
        "/v1/works:batch-check",
        json={
            "identities": [
                {"kind": "doi", "value": "10.1/seed"},
                {"kind": "doi", "value": "10.1/nope"},
            ]
        },
    )
    assert mixed.status_code == 200
    assert mixed.json()["rows"][0]["known"] is True
    denied = client.post(
        "/v1/uploads",
        files={"file": ("x.pdf", b"%PDF", "application/pdf")},
        data={"consent_destination": "elsewhere", "subcategory": "two_d_codes"},
    )
    assert denied.status_code == 400
    uploaded = client.post(
        "/v1/uploads",
        files={"file": ("x.pdf", b"%PDF", "application/pdf")},
        data={"consent_destination": "delphi", "subcategory": "two_d_codes"},
    )
    assert uploaded.status_code == 200
    missing = client.get(
        f"/v1/works/{uuid4()}/neighborhood",
        params={"mode": "citation", "subcategory": "two_d_codes"},
    )
    assert missing.status_code == 404
    neighborhood = client.get(
        f"/v1/works/{seed.id}/neighborhood",
        params={"mode": "union", "subcategory": "two_d_codes"},
    )
    assert neighborhood.status_code == 200
    generated = client.post(
        "/v1/generate",
        json={
            "kind": "research_path",
            "subcategory": "two_d_codes",
            "seed_work_id": str(seed.id),
        },
    )
    assert generated.status_code == 200
    assert generated.json()[0]["title"] == "Next 2D-code experiment"
    wrong = client.post(
        "/v1/generate",
        json={
            "kind": "research_path",
            "subcategory": "steganography",
            "seed_work_id": str(seed.id),
        },
    )
    assert wrong.status_code == 422
    absent = client.post(
        "/v1/generate",
        json={"kind": "research_path", "subcategory": "two_d_codes", "seed_work_id": str(uuid4())},
    )
    assert absent.status_code == 404


def test_generate_without_generator_and_upload_without_extractor() -> None:
    catalog = MemoryCatalog()
    seed = _work("QR", date(2014, 1, 1))
    catalog.upsert_work(seed)
    request = PathRequest(
        kind=PathKind.RESEARCH_PATH,
        subcategory="two_d_codes",
        seed_work_id=seed.id,
    )
    try:
        generate_paths(catalog, request, None)
    except MissingDependencyError:
        pass
    else:
        raise AssertionError("expected MissingDependencyError")
    app = create_app(AppContainer(catalog=catalog))
    client = TestClient(app)
    upload = client.post(
        "/v1/uploads",
        files={"file": ("x.pdf", b"%PDF", "application/pdf")},
        data={"consent_destination": "delphi", "subcategory": "two_d_codes"},
    )
    assert upload.status_code == 503
    generate = client.post(
        "/v1/generate",
        json={
            "kind": "patent_whitespace",
            "subcategory": "two_d_codes",
            "seed_work_id": str(seed.id),
        },
    )
    assert generate.status_code == 503


def test_work_from_extraction_defaults_and_helpers() -> None:
    extraction = Extraction(
        id=uuid4(),
        content_hash="d" * 64,
        title="Bare",
        body_text="body",
    )
    work = work_from_extraction(extraction, "two_d_codes")
    assert work.published_on == date(1970, 1, 1)
    assert work.keywords == ()
    identity = Identity(kind=IdentityKind.DOI, value="10.1/x")
    assert work_id_for(identity)
    unknown = work_from_extraction(extraction, "not_a_real_subcategory")
    assert unknown.categories[0].subcategory is None


def test_extraction_seed_and_edge_without_other_work() -> None:
    catalog = MemoryCatalog()
    extraction = Extraction(id=uuid4(), content_hash="e" * 64, title="From extract", body_text="x")
    catalog.put_extraction(extraction)
    work = work_from_extraction(extraction, "two_d_codes")
    catalog.upsert_work(work)
    request = PathRequest(
        kind=PathKind.RESEARCH_PATH,
        subcategory="two_d_codes",
        extraction_id=extraction.id,
        as_of=date(2016, 1, 1),
    )
    proposals = generate_paths(catalog, request, _Generator())
    assert proposals[0].kind is PathKind.RESEARCH_PATH
    dangling = Edge(from_work=work.id, to_work=uuid4(), kind=EdgeKind.CITES)
    catalog.add_edge(dangling)
    neighborhood = catalog.neighborhood(work.id, NeighborhoodMode.CITATION, "two_d_codes")
    assert neighborhood.neighbors == ()
    assert catalog.get_extraction(extraction.id) is not None
    assert catalog.get_extraction(uuid4()) is None
    assert catalog.get_work(uuid4()) is None
    assert catalog.list_works()
    assert catalog.edges()
    create_app()
    health = TestClient(create_app()).get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["catalog"] == "MemoryCatalog"


def test_identity_index_url_doi_and_stale_keys() -> None:
    catalog = MemoryCatalog()
    work = _work("QR", date(2014, 1, 1), "10.1/qr")
    catalog.upsert_work(work)
    request = BatchCheckRequest(
        identities=(Identity(kind=IdentityKind.DOI, value="https://doi.org/10.1/QR"),)
    )
    assert catalog.batch_check(request).rows[0].known is True
    replaced = work.model_copy(
        update={"identities": (Identity(kind=IdentityKind.DOI, value="10.1/new"),)}
    )
    catalog.upsert_work(replaced)
    stale = BatchCheckRequest(identities=(Identity(kind=IdentityKind.DOI, value="10.1/qr"),))
    assert catalog.batch_check(stale).rows[0].known is False
    fresh = BatchCheckRequest(identities=(Identity(kind=IdentityKind.DOI, value="10.1/new"),))
    assert catalog.batch_check(fresh).rows[0].known is True


def test_rebuild_all_and_skip_foreign_identity() -> None:
    catalog = MemoryCatalog()
    owner = _work("owner", date(2014, 1, 1), "10.1/own")
    other = _work("other", date(2014, 2, 1), "10.1/oth")
    catalog.upsert_work(owner)
    catalog.upsert_work(other)
    thief = _work("thief", date(2014, 3, 1), "10.1/own")
    with pytest.raises(ValueError, match="belongs to another work"):
        catalog.upsert_work(thief)
    check = catalog.batch_check(
        BatchCheckRequest(identities=(Identity(kind=IdentityKind.DOI, value="10.1/own"),))
    )
    assert check.rows[0].work_id == owner.id
    catalog.put_embedding(owner.id, hash_embed("owner text"), "m1")
    catalog.put_embedding(other.id, hash_embed("other text"), "m1")
    catalog.put_embedding(thief.id, hash_embed("thief text"), "m2")
    catalog.upsert_work(thief.model_copy(update={"identities": ()}))
    catalog.rebuild_all_similar_to(k=8)
    assert catalog.get_embedding(owner.id) is not None
    ranked = scored_neighbors(
        owner.id, hash_embed("owner text"), catalog._embeddings, catalog._models, "m1"
    )
    assert thief.id not in {item[0] for item in ranked}
    assert scored_neighbors(owner.id, (1.0,), {other.id: (1.0, 0.0)}) == []


def test_generate_holds_out_siblings_and_placeholder_dates() -> None:
    catalog = MemoryCatalog()
    seed = _work("QR 2014", date(2014, 6, 1), "10.1/s")
    held = _work("QR 2016", date(2016, 3, 1), "10.1/h")
    sibling = _work("same day", date(2016, 3, 1), "10.1/sib")
    catalog.upsert_work(seed)
    catalog.upsert_work(held)
    catalog.upsert_work(sibling)
    catalog.add_edge(Edge(from_work=seed.id, to_work=held.id, kind=EdgeKind.SIMILAR_TO, score=0.9))
    catalog.add_edge(
        Edge(from_work=seed.id, to_work=sibling.id, kind=EdgeKind.SIMILAR_TO, score=0.8)
    )
    request = PathRequest(
        kind=PathKind.RESEARCH_PATH, subcategory="two_d_codes", seed_work_id=seed.id
    )
    context = build_masked_context(catalog, request, held_out_ids=(held.id,))
    assert sibling.id not in {item.work.id for item in context.neighborhood.neighbors}
    assert held.id not in {item.work.id for item in context.neighborhood.neighbors}
    proposals = generate_paths(catalog, request, _Generator(), held_out_ids=(held.id,))
    assert proposals[0].kind is PathKind.RESEARCH_PATH
    with pytest.raises(KeyError):
        generate_paths(catalog, request, _Generator(), held_out_ids=(held.id, uuid4()))
    unknown = _work("undated", date(1970, 1, 1), "10.1/u")
    catalog.upsert_work(unknown)
    bounded = PathRequest(
        kind=PathKind.RESEARCH_PATH,
        subcategory="two_d_codes",
        seed_work_id=unknown.id,
        as_of=date(2015, 1, 1),
    )
    assert generate_paths(catalog, bounded, _Generator())
    open_ended = PathRequest(
        kind=PathKind.RESEARCH_PATH, subcategory="two_d_codes", seed_work_id=unknown.id
    )
    with pytest.raises(ValueError, match="publication date"):
        generate_paths(catalog, open_ended, _Generator())
    missing = BibliographyEntry(raw="no doi")
    assert attach_bibliography(catalog, seed.id, (missing,))[0].matched_work_id is None


def test_generate_context_leak_returns_422() -> None:
    catalog = MemoryCatalog()
    seed = _work("QR", date(2014, 1, 1), "10.1/z")
    catalog.upsert_work(seed)

    class _Boom:
        def generate(self, context: MaskedContext) -> tuple[PathProposal, ...]:
            raise ContextLeakError("leaked")

    client = TestClient(create_app(AppContainer(catalog=catalog, generator=_Boom())))
    response = client.post(
        "/v1/generate",
        json={
            "kind": "research_path",
            "subcategory": "two_d_codes",
            "seed_work_id": str(seed.id),
        },
    )
    assert response.status_code == 422
