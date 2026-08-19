"""HTTP client for the Delphi prototype API."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import httpx
from delphi_contracts.batch import BatchCheckRequest, BatchCheckResponse
from delphi_contracts.enums import NeighborhoodMode
from delphi_contracts.identity import Identity
from delphi_contracts.paths import PathKind

__all__ = ["DelphiClient"]


class DelphiClient:
    """Thin HTTP wrapper used by the CLI."""

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        """Store base URL and optional injected client.

        Args:
            base_url: Delphi origin.
            client: Injected httpx client for tests.
        """
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client()
        self._owns_client = client is None

    def close(self) -> None:
        """Close an owned HTTP client."""
        if self._owns_client:
            self._client.close()

    def batch_check(self, identities: tuple[Identity, ...]) -> BatchCheckResponse:
        """POST /v1/works:batch-check.

        Args:
            identities: Identifiers.

        Returns:
            Known/unknown rows.
        """
        request = BatchCheckRequest(identities=identities)
        response = self._client.post(
            f"{self._base}/v1/works:batch-check",
            json=request.model_dump(mode="json"),
        )
        response.raise_for_status()
        return BatchCheckResponse.model_validate(response.json())

    def neighborhood(
        self, work_id: UUID, mode: NeighborhoodMode, subcategory: str
    ) -> dict[str, object]:
        """GET neighborhood JSON.

        Args:
            work_id: Seed.
            mode: citation, content, or union.
            subcategory: Filter.

        Returns:
            Parsed JSON object.
        """
        response = self._client.get(
            f"{self._base}/v1/works/{work_id}/neighborhood",
            params={"mode": mode.value, "subcategory": subcategory},
        )
        response.raise_for_status()
        return dict(response.json())

    def upload(self, pdf_path: Path, destination: str, subcategory: str) -> dict[str, object]:
        """POST a consented PDF.

        Args:
            pdf_path: File to upload.
            destination: Consent destination (must be delphi).
            subcategory: Content-graph filter.

        Returns:
            Extraction plus neighborhood JSON.
        """
        with pdf_path.open("rb") as handle:
            response = self._client.post(
                f"{self._base}/v1/uploads",
                files={"file": (pdf_path.name, handle, "application/pdf")},
                data={"consent_destination": destination, "subcategory": subcategory},
            )
        response.raise_for_status()
        return dict(response.json())

    def generate(self, kind: PathKind, subcategory: str, seed_work_id: UUID) -> object:
        """POST /v1/generate.

        Args:
            kind: research_path or patent_whitespace.
            subcategory: Filter.
            seed_work_id: Seed work.

        Returns:
            Parsed JSON proposals.
        """
        response = self._client.post(
            f"{self._base}/v1/generate",
            json={
                "kind": kind.value,
                "subcategory": subcategory,
                "seed_work_id": str(seed_work_id),
            },
        )
        response.raise_for_status()
        return response.json()
