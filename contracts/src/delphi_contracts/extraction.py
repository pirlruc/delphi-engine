"""PDF upload consent and extraction output."""

from datetime import date
from typing import Annotated
from uuid import UUID

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, ConfigDict

from delphi_contracts.category import Category
from delphi_contracts.identity import Identity

__all__ = ["BibliographyEntry", "Extraction", "PdfUpload"]

CONSENT_DESTINATION = "delphi"


class PdfUpload(BaseModel):
    """Consent metadata that must accompany PDF bytes.

    Attributes:
        consent_destination: Must name delphi as the destination.
        filename: Original filename for logs.
        content_hash: SHA-256 hex of the PDF bytes.
    """

    model_config = ConfigDict(frozen=True)

    consent_destination: Annotated[str, MinLen(1)]
    filename: Annotated[str, MinLen(1)]
    content_hash: Annotated[str, MinLen(32), MaxLen(64)]


class BibliographyEntry(BaseModel):
    """One extracted citation, possibly unresolved.

    Attributes:
        raw: Bibliography string as extracted.
        identity: Parsed identifier when present.
        title: Parsed title when present.
        year: Parsed year when present.
        matched_work_id: Catalog work when batch-check resolves the cite.
    """

    model_config = ConfigDict(frozen=True)

    raw: Annotated[str, MinLen(1)]
    identity: Identity | None = None
    title: str | None = None
    year: int | None = None
    matched_work_id: UUID | None = None


class Extraction(BaseModel):
    """Structured fields taken from a consented PDF.

    Attributes:
        id: Extraction UUID (often the work id after upsert).
        content_hash: SHA-256 of source bytes.
        title: Extracted title.
        authors: Extracted authors.
        keywords: Extracted keywords.
        published_on: Extracted date when present.
        identities: Extracted identifiers.
        bibliography: Parsed bibliography rows.
        body_text: Extracted body used for the content graph.
        suggested_categories: LLM-suggested filters; user may override.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    content_hash: Annotated[str, MinLen(32)]
    title: Annotated[str, MinLen(1)]
    authors: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    published_on: date | None = None
    identities: tuple[Identity, ...] = ()
    bibliography: tuple[BibliographyEntry, ...] = ()
    body_text: str = ""
    suggested_categories: tuple[Category, ...] = ()
