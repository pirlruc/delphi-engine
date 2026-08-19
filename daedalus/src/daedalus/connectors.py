"""Map OpenAlex-shaped and PatentsView-shaped dicts onto Work records."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from delphi_contracts.category import Category
from delphi_contracts.enums import CategoryScheme, IdentityKind, SubcategoryId, WorkKind
from delphi_contracts.identity import Identity
from delphi_contracts.work import Work

__all__ = [
    "from_epo",
    "from_lens",
    "from_openalex",
    "from_patsnap",
    "from_patentsview",
    "from_wipo",
]


def from_openalex(record: dict[str, Any], subcategory: str) -> Work:
    """Map an OpenAlex-like dict to a Work.

    Args:
        record: Keys id, title, publication_date, doi, abstract, authors, keywords.
        subcategory: SYS-009 id.

    Returns:
        Catalog work.
    """
    return _from_common(record, WorkKind.PAPER, IdentityKind.DOI, "doi", subcategory)


def from_patentsview(record: dict[str, Any], subcategory: str) -> Work:
    """Map a PatentsView-like dict to a Work.

    Args:
        record: Keys id, title, publication_date, patent, abstract, authors, keywords.
        subcategory: SYS-009 id.

    Returns:
        Catalog work.
    """
    return _from_common(record, WorkKind.PATENT, IdentityKind.PATENT, "patent_id", subcategory)


def from_epo(record: dict[str, Any], subcategory: str) -> Work:
    """Map an EPO OPS ingest dict to a Work.

    Args:
        record: Fixture-shaped patent dict.
        subcategory: SYS-009 id.

    Returns:
        Catalog work.
    """
    return _from_common(record, WorkKind.PATENT, IdentityKind.PATENT, "patent", subcategory)


def from_wipo(record: dict[str, Any], subcategory: str) -> Work:
    """Map a WIPO PATENTSCOPE ingest dict to a Work.

    Args:
        record: Fixture-shaped patent dict.
        subcategory: SYS-009 id.

    Returns:
        Catalog work.
    """
    return from_epo(record, subcategory)


def from_patsnap(record: dict[str, Any], subcategory: str) -> Work:
    """Map a PatSnap ingest dict to a Work.

    Args:
        record: Fixture-shaped patent dict.
        subcategory: SYS-009 id.

    Returns:
        Catalog work.
    """
    return from_epo(record, subcategory)


def from_lens(record: dict[str, Any], subcategory: str) -> Work:
    """Map a Lens.org ingest dict to a Work.

    Args:
        record: Fixture-shaped patent dict.
        subcategory: SYS-009 id.

    Returns:
        Catalog work.
    """
    return from_epo(record, subcategory)


def _from_common(
    record: dict[str, Any],
    kind: WorkKind,
    identity_kind: IdentityKind,
    identity_key: str,
    subcategory: str,
) -> Work:
    """Shared mapper for paper and patent dicts.

    Args:
        record: Source dict.
        kind: Paper or patent.
        identity_kind: DOI or patent.
        identity_key: Key holding the identifier.
        subcategory: SYS-009 id.

    Returns:
        Work.
    """
    work_id = UUID(str(record["id"]))
    ident_value = str(
        record.get(identity_key) or record.get("doi") or record.get("patent") or work_id
    )
    authors = tuple(str(item) for item in record.get("authors", ()))
    keywords = tuple(str(item) for item in record.get("keywords", ()))
    known = {item.value for item in SubcategoryId}
    parsed = SubcategoryId(subcategory) if subcategory in known else None
    category = Category(
        scheme=CategoryScheme.CPC if kind is WorkKind.PATENT else CategoryScheme.OPENALEX_TOPIC,
        code=subcategory,
        label=subcategory.replace("_", " "),
        subcategory=parsed,
    )
    published = str(record.get("publication_date") or record.get("published_on") or "")
    return Work(
        id=work_id,
        kind=kind,
        title=str(record["title"]),
        authors=authors,
        keywords=keywords,
        abstract=str(record.get("abstract", "")),
        published_on=date.fromisoformat(published),
        identities=(Identity(kind=identity_kind, value=ident_value),),
        categories=(category,),
    )
