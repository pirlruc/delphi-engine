"""Daedalus ingest and extraction tests."""

from io import BytesIO
from pathlib import Path
from uuid import UUID

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
