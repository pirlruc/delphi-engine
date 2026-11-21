"""Hindcasting eval artifacts."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from annotated_types import Ge, Le
from pydantic import BaseModel, ConfigDict, Field

from delphi_contracts.enums import PathKind, ProviderKind

__all__ = ["EvalRun", "EvalScores"]


def _utcnow() -> datetime:
    """Return the current UTC time.

    Returns:
        Aware datetime.
    """
    return datetime.now(UTC)


class EvalScores(BaseModel):
    """Judge and embedding scores for one proposal vs held-out work.

    Attributes:
        novelty: Judge novelty 1-5.
        relevance: Judge relevance 1-5.
        accuracy: Judge accuracy 1-5.
        embedding_similarity: Cosine similarity vs held-out text.
    """

    model_config = ConfigDict(frozen=True)

    novelty: Annotated[float, Ge(1.0), Le(5.0)]
    relevance: Annotated[float, Ge(1.0), Le(5.0)]
    accuracy: Annotated[float, Ge(1.0), Le(5.0)]
    embedding_similarity: Annotated[float, Ge(0.0), Le(1.0)]


class EvalRun(BaseModel):
    """One hindcast trial record.

    Attributes:
        id: Run UUID.
        held_out_id: Hidden work.
        seed_id: Seed used for generation.
        kind: Query kind.
        subcategory: Filter used.
        provider: SYS-006 adapter that ran.
        model_id: Model identifier recorded for the run.
        scores: Aggregated scores.
        created_at: UTC timestamp.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    held_out_id: UUID
    seed_id: UUID
    kind: PathKind
    subcategory: str
    provider: ProviderKind
    model_id: str
    scores: EvalScores
    created_at: datetime = Field(default_factory=_utcnow)
