#!/usr/bin/env python3
"""PROTO-007 demo.

Upload a sample PDF, show both graphs, generate both kinds, and hindcast.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from daedalus.embed import HashEmbedder
from daedalus.extract import PdfExtractor
from daedalus.fixtures.sample import sample_pdf_bytes
from daedalus.ingest import ingest_records, load_fixture
from delphi.catalog import MemoryCatalog
from delphi.services import generate_paths, upload_pdf
from delphi_contracts.enums import NeighborhoodMode, PathKind
from delphi_contracts.json_tree import as_dict, namespace_dict, parse_json
from delphi_contracts.paths import PathRequest
from delphi_prometheus import PathGenerator
from epimetheus.trials import summarize_runs, trials_from_payload

_SEED = UUID("11111111-1111-1111-1111-111111111111")


def run_demo() -> dict[str, object]:
    """Execute the PDF demo and slice hindcast in-process.

    Returns:
        Artifact covering PROTO-007 acceptance.
    """
    catalog = MemoryCatalog()
    ingest_records(catalog, load_fixture())
    embedder = HashEmbedder(catalog)
    for work in catalog.list_works():
        embedder.embed_and_link(work)
    extraction, neighborhood = upload_pdf(
        catalog,
        sample_pdf_bytes(),
        "sample-qr.pdf",
        "delphi",
        "two_d_codes",
        PdfExtractor(),
        embedder,
    )
    citation = catalog.neighborhood(
        extraction.id, NeighborhoodMode.CITATION, "two_d_codes"
    )
    content = catalog.neighborhood(
        extraction.id, NeighborhoodMode.CONTENT, "two_d_codes"
    )
    generator = PathGenerator()
    research = generate_paths(
        catalog,
        PathRequest(
            kind=PathKind.RESEARCH_PATH,
            subcategory="two_d_codes",
            seed_work_id=extraction.id,
        ),
        generator,
    )
    patent = generate_paths(
        catalog,
        PathRequest(
            kind=PathKind.PATENT_WHITESPACE,
            subcategory="two_d_codes",
            seed_work_id=extraction.id,
        ),
        generator,
    )
    fixture = (
        Path(__file__).resolve().parent.parent
        / "daedalus"
        / "src"
        / "daedalus"
        / "fixtures"
        / "slice.json"
    )
    summary = summarize_runs(
        trials_from_payload(as_dict(parse_json(fixture.read_text(encoding="utf-8"))))
    )
    matched = sum(
        1 for row in extraction.bibliography if row.matched_work_id is not None
    )
    return {
        "extraction": {
            "title": extraction.title,
            "authors": list(extraction.authors),
            "keywords": list(extraction.keywords),
            "bibliography_matched": matched,
            "bibliography_total": len(extraction.bibliography),
        },
        "union_neighbors": len(neighborhood.neighbors),
        "citation_neighbors": len(citation.neighbors),
        "content_neighbors": len(content.neighbors),
        "research_path": research[0].title,
        "patent_whitespace": patent[0].title,
        "seed_work_id": str(_SEED),
        "uploaded_work_id": str(extraction.id),
        "hindcast": summary,
    }


def main(argv: list[str] | None = None) -> int:
    """Write the demo artifact.

    Args:
        argv: Optional CLI args.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(description="Delphi prototype demo")
    parser.add_argument("--output", type=Path, default=Path("docs/prototype-demo.json"))
    raw = namespace_dict(parser.parse_args(argv))
    output = raw.get("output")
    destination = (
        output if isinstance(output, Path) else Path("docs/prototype-demo.json")
    )
    artifact = run_demo()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
