"""PDF extraction via SYS-006 providers."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from io import BytesIO
from uuid import NAMESPACE_URL, uuid5

from delphi_contracts.enums import IdentityKind
from delphi_contracts.extraction import BibliographyEntry, Extraction
from delphi_contracts.identity import Identity, normalize_doi
from delphi_contracts.llm import ChatMessage, ChatRequest, LlmProvider, build_provider
from pypdf import PdfReader

__all__ = ["ExtractError", "PdfExtractor", "pdf_text"]

_DOI_RE = re.compile(r"10\.\d{4,}/[^\s]+")


class ExtractError(RuntimeError):
    """Raised when extraction fails after retries."""


def pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from a PDF.

    Args:
        pdf_bytes: Raw PDF.

    Returns:
        Concatenated page text.
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


class PdfExtractor:
    """Daedalus extractor using the shared LLM provider."""

    def __init__(self, llm: LlmProvider | None = None, attempts: int = 3) -> None:
        """Store the provider.

        Args:
            llm: SYS-006 adapter. Defaults to Fake.
            attempts: LLM retries before ExtractError.
        """
        self._llm = llm or build_provider()
        self._attempts = attempts

    def extract(self, pdf_bytes: bytes, filename: str) -> Extraction:
        """Parse a PDF into structured fields.

        Args:
            pdf_bytes: Raw PDF.
            filename: Original name.

        Returns:
            Extraction with bibliography and body text.
        """
        text = pdf_text(pdf_bytes)
        digest = sha256(pdf_bytes).hexdigest()
        prompt = f"Extract bibliographic metadata as JSON.\nFilename: {filename}\n{text}"
        last: Exception | None = None
        for _attempt in range(self._attempts):
            try:
                response = self._llm.chat(
                    ChatRequest(messages=(ChatMessage(role="user", content=prompt),))
                )
                return _extraction_from_payload(
                    json.loads(response.content), digest, filename, text
                )
            except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                last = exc
        raise ExtractError("extraction failed after retries") from last


def _extraction_from_payload(payload: object, digest: str, filename: str, text: str) -> Extraction:
    """Build an Extraction from LLM JSON.

    Args:
        payload: Parsed JSON.
        digest: Content hash.
        filename: Fallback title.
        text: PDF text fallback.

    Returns:
        Extraction.

    """
    if not isinstance(payload, dict):
        raise TypeError("extraction payload must be an object")
    raw_rows = payload.get("bibliography", [])
    rows = raw_rows if isinstance(raw_rows, list) else []
    bibliography = tuple(
        entry for entry in (_bibliography_entry(row) for row in rows) if entry is not None
    )
    raw_authors = payload.get("authors", ())
    authors = (
        tuple(str(item) for item in raw_authors) if isinstance(raw_authors, list | tuple) else ()
    )
    raw_keywords = payload.get("keywords", ())
    keywords = (
        tuple(str(item) for item in raw_keywords) if isinstance(raw_keywords, list | tuple) else ()
    )
    return Extraction(
        id=uuid5(NAMESPACE_URL, digest),
        content_hash=digest,
        title=str(payload.get("title") or filename),
        authors=authors,
        keywords=keywords,
        bibliography=bibliography,
        body_text=str(payload.get("body_text") or text),
    )


def _bibliography_entry(row: object) -> BibliographyEntry | None:
    """Parse one bibliography JSON object.

    Args:
        row: JSON value.

    Returns:
        Entry or None when the row is unusable.
    """
    if not isinstance(row, dict) or "raw" not in row:
        return None
    raw = str(row["raw"])
    doi_raw = row.get("doi")
    doi = _canonical_doi(str(doi_raw) if isinstance(doi_raw, str) else None) or _canonical_doi(raw)
    identity = Identity(kind=IdentityKind.DOI, value=doi) if doi else None
    return BibliographyEntry(raw=raw, identity=identity)


def _canonical_doi(text: str | None) -> str | None:
    """Return a DOI only when the string matches a resolver-safe pattern.

    Args:
        text: LLM field or bibliography line.

    Returns:
        Canonical DOI or None.
    """
    if not text:
        return None
    match = _DOI_RE.search(text)
    if match is None:
        return None
    return normalize_doi(match.group(0).rstrip(".,;)"))


def _doi_in(raw: str) -> str | None:
    """Return a DOI found in a bibliography line.

    Args:
        raw: Bibliography text.

    Returns:
        DOI or None.
    """
    return _canonical_doi(raw)
