"""Batch identifier existence checks."""

from typing import Annotated
from uuid import UUID

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, ConfigDict

from delphi_contracts.identity import Identity

__all__ = ["BatchCheckRequest", "BatchCheckResponse", "BatchCheckRow"]


class BatchCheckRequest(BaseModel):
    """Identifiers to resolve without uploading a PDF.

    Attributes:
        identities: Rows to look up. Order is preserved in the response.
    """

    model_config = ConfigDict(frozen=True)

    identities: Annotated[tuple[Identity, ...], MinLen(1), MaxLen(500)]


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
