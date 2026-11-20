"""Closed enumerations used across packages."""

from enum import StrEnum


class IdentityKind(StrEnum):
    """External identifier scheme for a work."""

    DOI = "doi"
    ARXIV = "arxiv"
    OPENALEX = "openalex"
    PATENT = "patent"
    CONTENT_HASH = "content_hash"


class WorkKind(StrEnum):
    """Catalog node type."""

    PAPER = "paper"
    PATENT = "patent"


class CategoryScheme(StrEnum):
    """Taxonomy a category code belongs to."""

    OPENALEX_TOPIC = "openalex_topic"
    CPC = "cpc"


class SubcategoryId(StrEnum):
    """Prototype subcategory filters (SYS-009)."""

    TRANSFORMERS_FOUNDATION_MODELS = "transformers_foundation_models"
    COMPUTER_VISION = "computer_vision"
    STEGANOGRAPHY = "steganography"
    TWO_D_CODES = "two_d_codes"


class EdgeKind(StrEnum):
    """Stored graph edge kind."""

    CITES = "cites"
    SIMILAR_TO = "similar_to"


class NeighborhoodMode(StrEnum):
    """Which graph a neighborhood query walks."""

    CITATION = "citation"
    CONTENT = "content"
    UNION = "union"


class PathKind(StrEnum):
    """Generator output kind."""

    RESEARCH_PATH = "research_path"
    PATENT_WHITESPACE = "patent_whitespace"


class ProviderKind(StrEnum):
    """SYS-006 LLM adapter selection."""

    CLOUD = "cloud"
    LOCAL = "local"
    FAKE = "fake"


class NeighborDirection(StrEnum):
    """Edge direction relative to the seed work."""

    IN = "in"
    OUT = "out"
