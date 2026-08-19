"""PDF extraction via SYS-006 providers."""

from __future__ import annotations

import json
from hashlib import sha256
from io import BytesIO
from uuid import NAMESPACE_URL, uuid5

from delphi_contracts.extraction import BibliographyEntry, Extraction
from delphi_contracts.llm import ChatMessage, ChatRequest, LlmProvider, build_provider
from pypdf import PdfReader

__all__ = ["PdfExtractor", "pdf_text"]


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

    def __init__(self, llm: LlmProvider | None = None) -> None:
        """Store the provider.

        Args:
            llm: SYS-006 adapter. Defaults to Fake.
        """
        self._llm = llm or build_provider()

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
        response = self._llm.chat(ChatRequest(messages=(ChatMessage(role="user", content=prompt),)))
        payload = json.loads(response.content)
        bibliography = tuple(
            BibliographyEntry(raw=str(row["raw"]))
            for row in payload.get("bibliography", [])
            if isinstance(row, dict) and "raw" in row
        )
        authors = tuple(str(item) for item in payload.get("authors", ()))
        keywords = tuple(str(item) for item in payload.get("keywords", ()))
        return Extraction(
            id=uuid5(NAMESPACE_URL, digest),
            content_hash=digest,
            title=str(payload.get("title") or filename),
            authors=authors,
            keywords=keywords,
            bibliography=bibliography,
            body_text=str(payload.get("body_text") or text),
        )
