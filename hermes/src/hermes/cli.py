"""Hermes prototype CLI."""

from __future__ import annotations

from datetime import date
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
    patent: Annotated[str | None, typer.Option()] = None,
    base_url: Annotated[str, typer.Option()] = _DEFAULT_URL,
    cache_path: Annotated[Path, typer.Option()] = _DEFAULT_CACHE,
) -> None:
    """Check whether identifiers exist without uploading a PDF.

    Args:
        doi: Optional DOI.
        arxiv: Optional arXiv id.
        patent: Optional patent number.
        base_url: Delphi origin.
        cache_path: Local SQLite cache.
    """
    identities: list[Identity] = []
    if doi:
        identities.append(Identity(kind=IdentityKind.DOI, value=doi))
    if arxiv:
        identities.append(Identity(kind=IdentityKind.ARXIV, value=arxiv))
    if patent:
        identities.append(Identity(kind=IdentityKind.PATENT, value=patent))
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
    _print_upload(payload)


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
    _print_neighborhood(payload)


@app.command()
def generate(
    kind: Annotated[PathKind, typer.Argument()],
    subcategory: Annotated[str, typer.Option()],
    seed_work_id: Annotated[UUID | None, typer.Option()] = None,
    extraction_id: Annotated[UUID | None, typer.Option()] = None,
    as_of: Annotated[str | None, typer.Option()] = None,
    base_url: Annotated[str, typer.Option()] = _DEFAULT_URL,
    cache_path: Annotated[Path, typer.Option()] = _DEFAULT_CACHE,
) -> None:
    """Ask for a research path or patent whitespace.

    Args:
        kind: research_path or patent_whitespace.
        subcategory: Filter.
        seed_work_id: Seed work.
        extraction_id: Uploaded extraction when the seed is not a catalog id.
        as_of: Inclusive temporal bound (YYYY-MM-DD).
        base_url: Delphi origin.
        cache_path: Local SQLite cache.
    """
    if seed_work_id is None and extraction_id is None:
        raise typer.Exit(code=2)
    bound = _parse_as_of(as_of)
    client = _client(base_url)
    try:
        payload = client.generate(
            kind,
            subcategory,
            seed_work_id,
            extraction_id=extraction_id,
            as_of=bound,
        )
    finally:
        client.close()
    _cache(cache_path).put("generate", payload)
    typer.echo(payload)


@app.command()
def reprint(
    name: Annotated[str, typer.Argument()],
    cache_path: Annotated[Path, typer.Option()] = _DEFAULT_CACHE,
) -> None:
    """Print the last cached JSON for a command name.

    Args:
        name: batch-check, upload, neighborhood, or generate.
        cache_path: Local SQLite cache.
    """
    payload = _cache(cache_path).get(name)
    if payload is None:
        raise typer.Exit(code=2)
    typer.echo(payload)


def _parse_as_of(value: str | None) -> str | None:
    """Validate an optional YYYY-MM-DD bound.

    Args:
        value: CLI ``--as-of`` string.

    Returns:
        The same string when valid, or None.

    Raises:
        typer.BadParameter: When the value is not an ISO date.
    """
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("as_of must be YYYY-MM-DD") from exc
    return value


def _print_upload(payload: object) -> None:
    """Print extracted metadata and bibliography match counts.

    Args:
        payload: Upload JSON.
    """
    if not isinstance(payload, dict):
        typer.echo(payload)
        return
    extraction = payload.get("extraction", {})
    if not isinstance(extraction, dict):
        typer.echo(payload)
        return
    bibliography = extraction.get("bibliography", [])
    rows = bibliography if isinstance(bibliography, list) else []
    matched = sum(1 for row in rows if isinstance(row, dict) and row.get("matched_work_id"))
    typer.echo(f"title: {extraction.get('title')}")
    typer.echo(f"authors: {extraction.get('authors')}")
    typer.echo(f"keywords: {extraction.get('keywords')}")
    typer.echo(f"bibliography: {matched}/{len(rows)} matched")
    _print_neighborhood(payload.get("neighborhood"))


def _print_neighborhood(payload: object) -> None:
    """Print citation vs content neighbor counts.

    Args:
        payload: Neighborhood JSON.
    """
    if not isinstance(payload, dict):
        typer.echo(payload)
        return
    neighbors = payload.get("neighbors", [])
    rows = neighbors if isinstance(neighbors, list) else []
    cites = sum(1 for row in rows if isinstance(row, dict) and row.get("edge_kind") == "cites")
    similar = sum(
        1 for row in rows if isinstance(row, dict) and row.get("edge_kind") == "similar_to"
    )
    typer.echo(f"neighbors: {cites} cites, {similar} similar_to ({len(rows)} total)")
