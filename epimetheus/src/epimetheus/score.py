"""LLM-as-judge plus embedding similarity."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from delphi_contracts.eval_run import EvalRun, EvalScores
from delphi_contracts.llm import (
    ChatMessage,
    ChatRequest,
    EmbedRequest,
    LlmProvider,
    build_provider,
    cosine,
)
from delphi_contracts.paths import PathProposal
from delphi_contracts.work import Work

__all__ = ["score_proposal"]


def score_proposal(
    proposal: PathProposal,
    held_out: Work,
    seed_id: UUID,
    subcategory: str,
    llm: LlmProvider | None = None,
) -> EvalRun:
    """Score a proposal against a held-out work.

    Args:
        proposal: Generator output.
        held_out: Hidden historical work.
        seed_id: Seed used for generation.
        subcategory: Filter.
        llm: SYS-006 provider. Defaults to Fake.

    Returns:
        EvalRun with judge scores and embedding similarity.
    """
    provider = llm or build_provider()
    prompt = (
        "llm-as-judge novelty relevance accuracy. "
        f"proposal={proposal.title} held_out={held_out.title}"
    )
    response = provider.chat(ChatRequest(messages=(ChatMessage(role="user", content=prompt),)))
    payload = json.loads(response.content)
    left = provider.embed(EmbedRequest(text=proposal.title + " " + " ".join(proposal.claims)))
    right = provider.embed(EmbedRequest(text=f"{held_out.title} {held_out.abstract}"))
    scores = EvalScores(
        novelty=float(payload.get("novelty", 3)),
        relevance=float(payload.get("relevance", 3)),
        accuracy=float(payload.get("accuracy", 3)),
        embedding_similarity=cosine(left.vector, right.vector),
    )
    return EvalRun(
        id=uuid4(),
        held_out_id=held_out.id,
        seed_id=seed_id,
        kind=proposal.kind,
        subcategory=subcategory,
        provider=provider.kind,
        model_id=provider.model_id,
        scores=scores,
    )
