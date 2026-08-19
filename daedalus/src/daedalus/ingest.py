"""Load the SYS-009 fixture slice into a catalog writer."""

from __future__ import annotations

import json
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Any
from uuid import UUID

from delphi_contracts.category import Category
from delphi_contracts.enums import (
    CategoryScheme,
    EdgeKind,
    IdentityKind,
    SubcategoryId,
    WorkKind,
)
from delphi_contracts.graph import Edge
from delphi_contracts.identity import Identity
from delphi_contracts.work import Work

from daedalus.caps import allowed_text, check_caps
from daedalus.ports import CatalogWriter

__all__ = ["fixture_path", "ingest_records", "load_fixture"]


def fixture_path() -> Path:
    """Return the packaged slice JSON path.

    Returns:
        Path to slice.json.
    """
    return Path(str(files("daedalus.fixtures").joinpath("slice.json")))


def load_fixture(path: Path | None = None) -> list[dict[str, Any]]:
    """Load fixture records.

    Args:
        path: Optional JSON file. Defaults to the packaged slice.

    Returns:
        Work dicts.
    """
    payload = json.loads((path or fixture_path()).read_text(encoding="utf-8"))
    return list(payload["works"])


def ingest_records(catalog: CatalogWriter, records: list[dict[str, Any]]) -> int:
    """Upsert works and cites, enforcing SYS-009 caps.

    Args:
        catalog: Writer (typically Delphi's MemoryCatalog).
        records: Fixture or connector dicts.

    Returns:
        Number of works ingested.

    """
    counts: dict[str, int] = {}
    stored: list[tuple[Work, list[str]]] = []
    for record in records:
        subcategory = str(record["subcategory"])
        blob = f"{record.get('title', '')} {record.get('abstract', '')}"
        if not allowed_text(blob, subcategory):
            continue
        work = _work_from_fixture(record)
        stored.append((work, [str(item) for item in record.get("cites", [])]))
        counts[subcategory] = counts.get(subcategory, 0) + 1
    check_caps(counts)
    known = {work.id for work, _cites in stored}
    for work, _cites in stored:
        catalog.upsert_work(work)
    for work, cites in stored:
        for target in cites:
            try:
                other = UUID(str(target))
            except ValueError:
                continue
            if other in known:
                catalog.add_edge(Edge(from_work=work.id, to_work=other, kind=EdgeKind.CITES))
    return len(stored)


def _work_from_fixture(record: dict[str, Any]) -> Work:
    """Build a Work from fixture JSON.

    Args:
        record: Fixture row.

    Returns:
        Work.
    """
    subcategory = str(record["subcategory"])
    parsed = SubcategoryId(subcategory)
    scheme = CategoryScheme.CPC if record["kind"] == "patent" else CategoryScheme.OPENALEX_TOPIC
    identity = _identities(record)
    return Work(
        id=UUID(str(record["id"])),
        kind=WorkKind(str(record["kind"])),
        title=str(record["title"]),
        authors=tuple(str(item) for item in record.get("authors", ())),
        keywords=tuple(str(item) for item in record.get("keywords", ())),
        abstract=str(record.get("abstract", "")),
        published_on=date.fromisoformat(str(record["published_on"])),
        identities=identity,
        categories=(
            Category(
                scheme=scheme,
                code=subcategory,
                label=subcategory.replace("_", " "),
                subcategory=parsed,
            ),
        ),
    )


def _identities(record: dict[str, Any]) -> tuple[Identity, ...]:
    """Collect DOI, patent, OpenAlex, and arXiv identities.

    Args:
        record: Fixture or connector row.

    Returns:
        One or more identities; content hash when none are present.
    """
    mapping = (
        ("doi", IdentityKind.DOI),
        ("patent", IdentityKind.PATENT),
        ("openalex", IdentityKind.OPENALEX),
        ("arxiv", IdentityKind.ARXIV),
    )
    rows: list[Identity] = []
    seen: set[tuple[str, str]] = set()
    for key, kind in mapping:
        value = record.get(key)
        if not value:
            continue
        text = str(value)
        pair = (kind.value, text)
        if pair in seen:
            continue
        seen.add(pair)
        rows.append(Identity(kind=kind, value=text))
    if rows:
        return tuple(rows)
    return (Identity(kind=IdentityKind.CONTENT_HASH, value=str(record["id"])),)
