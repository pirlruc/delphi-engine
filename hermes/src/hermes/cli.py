"""Hermes prototype CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer
from delphi_contracts.enums import IdentityKind, NeighborhoodMode, PathKind
from delphi_contracts.extraction import CONSENT_DESTINATION
from delphi_contracts.identity import Identity

from hermes.cache import ResultCache
from hermes.client import DelphiClient

app = typer.Typer(help="Delphi Engine client")

_DEFAULT_URL = "http://127.0.0.1:8000"
_DEFAULT_CACHE = Path.home() / ".delphi" / "hermes.sqlite"


def _client(base_url: str) -> DelphiClient:
    """Build a Delphi HTTP client.

    Args:
        base_url: Origin.

    Returns:
        Client wrapper.
    """
    return DelphiClient(base_url)


def _cache(cache_path: Path) -> ResultCache:
    """Build a result cache.

    Args:
        cache_path: SQLite path.

    Returns:
        Cache.
    """
    return ResultCache(cache_path)


@app.command("batch-check")
def batch_check(
    doi: Annotated[str | None, typer.Option()] = None,
    arxiv: Annotated[str | None, typer.Option()] = None,
    base_url: Annotated[str, typer.Option()] = _DEFAULT_URL,
    cache_path: Annotated[Path, typer.Option()] = _DEFAULT_CACHE,
) -> None:
    """Check whether identifiers exist without uploading a PDF.

    Args:
        doi: Optional DOI.
        arxiv: Optional arXiv id.
        base_url: Delphi origin.
        cache_path: Local SQLite cache.
    """
    identities: list[Identity] = []
    if doi:
        identities.append(Identity(kind=IdentityKind.DOI, value=doi))
    if arxiv:
        identities.append(Identity(kind=IdentityKind.ARXIV, value=arxiv))
    if not identities:
        raise typer.Exit(code=2)
    client = _client(base_url)
    try:
        result = client.batch_check(tuple(identities))
    finally:
        client.close()
    payload = result.model_dump(mode="json")
    _cache(cache_path).put("batch-check", payload)
    typer.echo(payload)


@app.command()
def upload(
    pdf: Annotated[Path, typer.Argument()],
    subcategory: Annotated[str, typer.Option()],
    consent_destination: Annotated[str | None, typer.Option()] = None,
    base_url: Annotated[str, typer.Option()] = _DEFAULT_URL,
    cache_path: Annotated[Path, typer.Option()] = _DEFAULT_CACHE,
) -> None:
    """Upload one PDF after naming Delphi as destination.

    Args:
        pdf: PDF path.
        subcategory: SYS-009 filter.
        consent_destination: Must be delphi.
        base_url: Delphi origin.
        cache_path: Local SQLite cache.
    """
    if consent_destination != CONSENT_DESTINATION:
        raise typer.Exit(code=2)
    client = _client(base_url)
    try:
        payload = client.upload(pdf, consent_destination, subcategory)
    finally:
        client.close()
    _cache(cache_path).put("upload", payload)
    extraction = payload.get("extraction", {})
    typer.echo(extraction)


@app.command()
def neighborhood(
    work_id: Annotated[UUID, typer.Argument()],
    subcategory: Annotated[str, typer.Option()],
    mode: Annotated[NeighborhoodMode, typer.Option()] = NeighborhoodMode.UNION,
    base_url: Annotated[str, typer.Option()] = _DEFAULT_URL,
    cache_path: Annotated[Path, typer.Option()] = _DEFAULT_CACHE,
) -> None:
    """Show citation and/or content neighbors.

    Args:
        work_id: Seed work.
        subcategory: Filter.
        mode: citation, content, or union.
        base_url: Delphi origin.
        cache_path: Local SQLite cache.
    """
    client = _client(base_url)
    try:
        payload = client.neighborhood(work_id, mode, subcategory)
    finally:
        client.close()
    _cache(cache_path).put("neighborhood", payload)
    typer.echo(payload)


@app.command()
def generate(
    kind: Annotated[PathKind, typer.Argument()],
    subcategory: Annotated[str, typer.Option()],
    seed_work_id: Annotated[UUID, typer.Option()],
    base_url: Annotated[str, typer.Option()] = _DEFAULT_URL,
    cache_path: Annotated[Path, typer.Option()] = _DEFAULT_CACHE,
) -> None:
    """Ask for a research path or patent whitespace.

    Args:
        kind: research_path or patent_whitespace.
        subcategory: Filter.
        seed_work_id: Seed work.
        base_url: Delphi origin.
        cache_path: Local SQLite cache.
    """
    client = _client(base_url)
    try:
        payload = client.generate(kind, subcategory, seed_work_id)
    finally:
        client.close()
    _cache(cache_path).put("generate", payload)
    typer.echo(payload)
