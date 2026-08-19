"""Canonical work identifiers."""

from pydantic import BaseModel, ConfigDict, Field

from delphi_contracts.enums import IdentityKind

__all__ = ["Identity", "IdentityKind"]


class Identity(BaseModel):
    """One external identifier for a work.

    Attributes:
        kind: Identifier scheme.
        value: Scheme-specific value (DOI, arXiv id, OpenAlex id, patent number, hash).
    """

    model_config = ConfigDict(frozen=True)

    kind: IdentityKind
    value: str = Field(min_length=1)
