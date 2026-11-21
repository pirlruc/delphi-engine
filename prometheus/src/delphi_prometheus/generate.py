"""Generate research paths from a MaskedContext only."""

from __future__ import annotations

from uuid import UUID

from delphi_contracts.json_tree import as_dict, as_list, parse_json
from delphi_contracts.llm import ChatMessage, ChatRequest, LlmProvider, build_provider
from delphi_contracts.paths import (
    ContextLeakError,
    MaskedContext,
    PathKind,
    PathProposal,
)

__all__ = ["PathGenerator", "assert_no_leak"]


def assert_no_leak(context: MaskedContext) -> None:
    """Reject context that contains held-out or future works.

    Args:
        context: Candidate generator input.

    """
    present = {
        context.seed.id,
        *(item.work.id for item in context.neighborhood.neighbors),
    }
    leaked = (set(context.forbidden_ids()) | set(context.held_out_ids)) & present
    leaked.update(
        item.work.id
        for item in context.neighborhood.neighbors
        if item.work.published_on >= context.mask_on
    )
    if leaked:
        raise ContextLeakError(f"context leaks ids: {sorted(leaked)}")


class PathGenerator:
    """Prometheus generator. Must not fetch a catalog."""

    def __init__(self, llm: LlmProvider | None = None) -> None:
        """Store the SYS-006 provider.

        Args:
            llm: Adapter. Defaults to Fake.
        """
        self._llm = llm or build_provider()

    def generate(self, context: MaskedContext) -> tuple[PathProposal, ...]:
        """Propose ranked next steps from the masked neighborhood.

        Args:
            context: Past-only neighborhood tagged by edge kind.

        Returns:
            One or more structured proposals.

        """
        assert_no_leak(context)
        prompt = (
            f"propose the next {context.kind.value} from this masked context. "
            f"mask_on={context.mask_on.isoformat()} "
            f"seed={context.seed.id} "
            "neighbors="
            f"{[str(item.work.id) for item in context.neighborhood.neighbors]}"
        )
        response = self._llm.chat(
            ChatRequest(messages=(ChatMessage(role="user", content=prompt),))
        )
        payload = as_dict(parse_json(response.content))
        proposed = payload.get("proposals")
        rows = (
            [as_dict(item) for item in as_list(proposed)]
            if proposed is not None
            else [payload]
        )
        allowed = {
            context.seed.id,
            *(item.work.id for item in context.neighborhood.neighbors),
        }
        return tuple(_proposal(row, context.kind, allowed) for row in rows)


def _proposal(
    row: dict[str, object], default_kind: PathKind, allowed: set[UUID] | None = None
) -> PathProposal:
    """Parse one proposal dict.

    Args:
        row: JSON object.
        default_kind: Request kind fallback.
        allowed: Context work ids that may be cited. Unknown ids are dropped.

    Returns:
        PathProposal.
    """
    raw_cited = row.get("cited_work_ids", [])
    cited_values = raw_cited if isinstance(raw_cited, list) else []
    cited = tuple(UUID(str(item)) for item in cited_values)
    if allowed is not None:
        cited = tuple(item for item in cited if item in allowed)
    kind_raw = str(row.get("kind", default_kind.value))
    kinds = {item.value for item in PathKind}
    kind = PathKind(kind_raw) if kind_raw in kinds else default_kind
    raw_claims = row.get("claims", ["Next step."])
    claim_values = raw_claims if isinstance(raw_claims, list) else ["Next step."]
    claims = tuple(str(item) for item in claim_values)
    raw_rank = row.get("rank", 1)
    rank = int(raw_rank) if isinstance(raw_rank, int | str) else 1
    return PathProposal(
        kind=kind,
        title=str(row.get("title") or "Untitled proposal"),
        claims=claims or ("Next step.",),
        rationale=str(row.get("rationale") or "From masked context."),
        cited_work_ids=cited,
        rank=rank,
    )
