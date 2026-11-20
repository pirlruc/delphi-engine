"""Batch identifier existence checks."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from delphi_contracts.identity import Identity

__all__ = ["BatchCheckRequest", "BatchCheckResponse", "BatchCheckRow"]


class BatchCheckRequest(BaseModel):
    """Identifiers to resolve without uploading a PDF.

    Attributes:
        identities: Rows to look up. Order is preserved in the response.
    """

    model_config = ConfigDict(frozen=True)

    identities: tuple[Identity, ...] = Field(min_length=1, max_length=500)


class BatchCheckRow(BaseModel):
    """Known/unknown result for one identity.

    Attributes:
        identity: The queried identifier.
        known: True when the catalog has an exact match.
        work_id: Catalog UUID when known.
    """

    model_config = ConfigDict(frozen=True)

    identity: Identity
    known: bool
    work_id: UUID | None = None


class BatchCheckResponse(BaseModel):
    """Batch-check results in request order.

    Attributes:
        rows: One row per request identity.
    """

    model_config = ConfigDict(frozen=True)

    rows: tuple[BatchCheckRow, ...]
