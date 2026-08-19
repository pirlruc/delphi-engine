"""Hindcasting eval artifacts."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from delphi_contracts.enums import PathKind, ProviderKind

__all__ = ["EvalRun", "EvalScores"]


class EvalScores(BaseModel):
    """Judge and embedding scores for one proposal vs held-out work.

    Attributes:
        novelty: Judge novelty 1-5.
        relevance: Judge relevance 1-5.
        accuracy: Judge accuracy 1-5.
        embedding_similarity: Cosine similarity vs held-out text.
    """

    model_config = ConfigDict(frozen=True)

    novelty: float = Field(ge=1.0, le=5.0)
    relevance: float = Field(ge=1.0, le=5.0)
    accuracy: float = Field(ge=1.0, le=5.0)
    embedding_similarity: float = Field(ge=0.0, le=1.0)


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
