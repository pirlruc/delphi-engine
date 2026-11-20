"""Minimal PDF used by the prototype demo."""

from __future__ import annotations

__all__ = ["sample_pdf_bytes", "sample_pdf_text"]

_LINES = (
    "Title: Color QR overlay on packaging",
    "Authors: Ada Lovelace, Alan Turing",
    "Keywords: qr, watermarking",
    "1. Kim. QR Codes in Industrial Tracking. doi:10.1000/qr-2014",
    "Color QR codes that watermark packaging using data matrix lessons.",
)


def sample_pdf_text() -> str:
    """Return the bibliographic text embedded in the sample PDF.

    Returns:
        Plain text.
    """
    return "\n".join(_LINES)


def sample_pdf_bytes() -> bytes:
    """Return a one-page PDF containing the sample bibliographic text.

    Returns:
        PDF bytes.
    """
    commands = ["BT /F1 12 Tf 50 720 Td"]
    for index, line in enumerate(_LINES):
        if index:
            commands.append("0 -16 Td")
        commands.append(f"({_escape(line)}) Tj")
    commands.append("ET")
    stream = " ".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    position = 9
    for index, body in enumerate(objects, start=1):
        offsets.append(position)
        header = f"{index} 0 obj\n".encode("ascii")
        block = header + body + b"\nendobj\n"
        chunks.append(block)
        position += len(block)
    xref_pos = position
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode("ascii")
        + b"\n%%EOF\n"
    )
    return b"".join(chunks + xref + [trailer])


def _escape(line: str) -> str:
    """Escape a PDF literal string.

    Args:
        line: Raw text.

    Returns:
        Escaped text.
    """
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
