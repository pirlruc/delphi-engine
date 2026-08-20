"""Canonical work identifiers."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from delphi_contracts.enums import IdentityKind

__all__ = [
    "Identity",
    "IdentityKind",
    "normalize_doi",
    "normalize_identity",
    "normalize_patent",
]

_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)


def normalize_doi(value: str) -> str:
    """Strip URL/doi prefixes and lowercase a DOI.

    Args:
        value: Raw DOI or DOI URL.

    Returns:
        Bare lowercase DOI.
    """
    text = value.strip()
    lowered = text.lower()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.strip().lower()


def normalize_patent(value: str) -> str:
    """Uppercase a patent number and drop spaces and hyphens.

    Args:
        value: Raw office number.

    Returns:
        Stable identity string.
    """
    return value.upper().replace(" ", "").replace("-", "")


def normalize_identity(kind: IdentityKind, value: str) -> str:
    """Canonicalize an identity value for storage and lookup.

    Args:
        kind: Identifier scheme.
        value: Raw value.

    Returns:
        Normalized value.
    """
    if kind is IdentityKind.DOI:
        return normalize_doi(value)
    if kind is IdentityKind.PATENT:
        return normalize_patent(value)
    if kind is IdentityKind.ARXIV:
        text = value.strip().lower()
        return text.removeprefix("arxiv:")
    return value.strip()


class Identity(BaseModel):
    """One external identifier for a work.

    Attributes:
        kind: Identifier scheme.
        value: Scheme-specific value (DOI, arXiv id, OpenAlex id, patent number, hash).
    """

    model_config = ConfigDict(frozen=True)

    kind: IdentityKind
    value: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _canonicalize(cls, data: object) -> object:
        """Normalize DOI, patent, and arXiv values before validation.

        Args:
            data: Constructor payload.

        Returns:
            Payload with a canonical ``value`` when kind is known.
        """
        if not isinstance(data, dict):
            return data
        kind_raw = data.get("kind")
        value = data.get("value")
        try:
            kind = kind_raw if isinstance(kind_raw, IdentityKind) else IdentityKind(str(kind_raw))
        except ValueError:
            return data
        if not isinstance(value, str):
            return data
        return {**data, "value": normalize_identity(kind, value)}
