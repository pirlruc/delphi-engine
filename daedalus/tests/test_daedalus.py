"""Daedalus ingest and extraction tests."""

import json
from io import BytesIO
from pathlib import Path
from uuid import UUID

import httpx
from delphi.catalog import MemoryCatalog
from delphi_contracts.enums import WorkKind
from delphi_contracts.llm import FakeProvider
from pypdf import PdfWriter

from daedalus.caps import CapsError, allowed_text, check_caps
from daedalus.cli import main
from daedalus.connectors import from_openalex, from_patentsview
from daedalus.embed import HashEmbedder
from daedalus.extract import PdfExtractor, pdf_text
from daedalus.ingest import ingest_records, load_fixture


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_caps_and_cv_blocklist() -> None:
    assert allowed_text("qr codes", "two_d_codes") is True
    assert allowed_text("autonomous driving detector", "computer_vision") is False
    assert allowed_text("document images", "computer_vision") is True
    check_caps({"two_d_codes": 3, "transformers_foundation_models": 2})
    try:
        check_caps({"transformers_foundation_models": 5, "two_d_codes": 1})
    except CapsError:
        return
    raise AssertionError("expected CapsError")


def test_ingest_fixture_into_memory_catalog() -> None:
    catalog = MemoryCatalog()
    count = ingest_records(catalog, load_fixture())
    assert count == 8
    assert catalog.get_work(UUID("11111111-1111-1111-1111-111111111111")) is not None
    medical = [
        {
            "id": "99999999-9999-9999-9999-999999999999",
            "kind": "paper",
            "title": "Radiology medical imaging",
            "abstract": "autonomous driving plus medical imaging",
            "published_on": "2015-01-01",
            "doi": "10.1/med",
            "subcategory": "computer_vision",
            "cites": [],
        }
    ]
    assert ingest_records(catalog, medical) == 0


def test_ingest_hash_identity_and_caps_error() -> None:
    catalog = MemoryCatalog()
    records = [
        {
            "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "kind": "paper",
            "title": "FM 1",
            "published_on": "2018-01-01",
            "subcategory": "transformers_foundation_models",
        },
        {
            "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "kind": "paper",
            "title": "FM 2",
            "published_on": "2018-02-01",
            "subcategory": "transformers_foundation_models",
        },
    ]
    try:
        ingest_records(catalog, records)
    except CapsError:
        pass
    else:
        raise AssertionError("expected CapsError")
    hashed = ingest_records(
        catalog,
        [
            {
                "id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "kind": "paper",
                "title": "Hash id paper",
                "published_on": "2011-01-01",
                "subcategory": "steganography",
            }
        ],
    )
    assert hashed == 1


def test_connectors_map_records() -> None:
    paper = from_openalex(
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "title": "OpenAlex paper",
            "publication_date": "2014-01-01",
            "doi": "10.1/oa",
            "abstract": "qr",
            "authors": ["A"],
            "keywords": ["qr"],
        },
        "two_d_codes",
    )
    assert paper.kind is WorkKind.PAPER
    patent = from_patentsview(
        {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "title": "Patent",
            "publication_date": "2013-01-01",
            "patent_id": "US-1",
            "authors": ["B"],
        },
        "two_d_codes",
    )
    assert patent.kind is WorkKind.PATENT
    unknown = from_openalex(
        {
            "id": "abababab-abab-abab-abab-abababababab",
            "title": "No doi",
            "publication_date": "2014-01-01",
        },
        "not_real",
    )
    assert unknown.identities[0].value


def test_extract_embed_and_cli(tmp_path: Path) -> None:
    catalog = MemoryCatalog()
    ingest_records(catalog, load_fixture())
    extractor = PdfExtractor(FakeProvider())
    extraction = extractor.extract(_blank_pdf(), "upload.pdf")
    assert extraction.title
    seed = catalog.get_work(UUID("11111111-1111-1111-1111-111111111111"))
    assert seed is not None
    HashEmbedder(catalog).embed_and_link(seed, f"{seed.title} {seed.abstract}")
    assert catalog.get_embedding(seed.id) is not None
    assert isinstance(pdf_text(_blank_pdf()), str)
    assert main(["--dry-run"]) == 0
    assert main([]) == 0
    extra = tmp_path / "slice.json"
    extra.write_text(
        '{"works":[{"id":"cccccccc-cccc-cccc-cccc-cccccccccccc","kind":"paper",'
        '"title":"X","published_on":"2011-01-01","subcategory":"steganography"}]}'
    )
    catalog2 = MemoryCatalog()
    assert ingest_records(catalog2, load_fixture(extra)) == 1


def test_sample_pdf_retries_and_fetch(monkeypatch) -> None:
    from delphi_contracts.enums import ProviderKind
    from delphi_contracts.llm import ChatResponse, EmbedResponse

    from daedalus.extract import ExtractError
    from daedalus.fetch import FetchError, fetch_openalex, fetch_patentsview
    from daedalus.fixtures.sample import sample_pdf_bytes, sample_pdf_text

    extraction = PdfExtractor().extract(sample_pdf_bytes(), "sample-qr.pdf")
    assert "Color QR" in extraction.title
    assert extraction.bibliography
    assert extraction.bibliography[0].identity is not None
    assert "Title:" in sample_pdf_text()

    class _Flaky:
        kind = ProviderKind.FAKE
        model_id = "flaky"
        n = 0

        def chat(self, request):
            self.n += 1
            if self.n == 1:
                return ChatResponse(content="[]", model="flaky", provider=ProviderKind.FAKE)
            if self.n < 3:
                return ChatResponse(content="not-json", model="flaky", provider=ProviderKind.FAKE)
            return FakeProvider().chat(request)

        def embed(self, request):
            return FakeProvider().embed(request)

    recovered = PdfExtractor(llm=_Flaky()).extract(_blank_pdf(), "x.pdf")
    assert recovered.title

    class _Payload:
        kind = ProviderKind.FAKE
        model_id = "payload"

        def chat(self, request):
            payload = {
                "title": "From list bib",
                "authors": "bad",
                "keywords": "bad",
                "bibliography": [
                    1,
                    {"raw": "no identifier"},
                    {"raw": "x", "doi": 1},
                    {"raw": "see 10.1000/qr-2014."},
                ],
            }
            return ChatResponse(
                content=json.dumps(payload),
                model="payload",
                provider=ProviderKind.FAKE,
            )

        def embed(self, request):
            return FakeProvider().embed(request)

    parsed = PdfExtractor(llm=_Payload()).extract(_blank_pdf(), "x.pdf")
    assert parsed.title == "From list bib"
    assert any(entry.identity is not None for entry in parsed.bibliography)

    class _Dead:
        kind = ProviderKind.FAKE
        model_id = "dead"

        def chat(self, request):
            return ChatResponse(content="not-json", model="dead", provider=ProviderKind.FAKE)

        def embed(self, request):
            return EmbedResponse(vector=(), model="dead", provider=ProviderKind.FAKE)

    try:
        PdfExtractor(llm=_Dead(), attempts=2).extract(_blank_pdf(), "x.pdf")
    except ExtractError:
        pass
    else:
        raise AssertionError("expected ExtractError")

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if "openalex" in str(request.url):
            if calls["n"] < 2:
                return httpx.Response(500)
            return httpx.Response(
                200,
                json={
                    "results": [
                        "skip-me",
                        {"id": "https://openalex.org/W1"},
                        {
                            "id": "https://openalex.org/W2",
                            "title": "QR paper",
                            "publication_date": "2014-01-01",
                            "doi": "https://doi.org/10.1/x",
                            "authors": ["Ada"],
                            "keywords": ["qr"],
                        },
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "patents": [
                    "skip-me",
                    {"nope": True},
                    {
                        "patent_id": "US-1",
                        "patent_title": "Carrier",
                        "patent_date": "2013-01-01",
                    },
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    papers = fetch_openalex("http://openalex.test/works", "two_d_codes", client)
    assert len(papers) == 1
    patents = fetch_patentsview("http://patents.test/patents", "two_d_codes", client)
    assert len(patents) == 1

    def boom(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    dead = httpx.Client(transport=httpx.MockTransport(boom))
    try:
        fetch_openalex("http://openalex.test/fail", "two_d_codes", dead, attempts=2)
    except FetchError:
        pass
    else:
        raise AssertionError("expected FetchError")

    class _CM:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("daedalus.cli.httpx.Client", lambda: _CM())
    monkeypatch.setattr("daedalus.cli.fetch_openalex", lambda *_a, **_k: [{}, {}])
    monkeypatch.setattr("daedalus.cli.fetch_patentsview", lambda *_a, **_k: [{}])
    assert main(["--openalex-url", "http://x"]) == 0
    assert main(["--patentsview-url", "http://y"]) == 0
