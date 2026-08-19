"""Shared schema for Delphi Engine."""

from delphi_contracts.batch import BatchCheckRequest, BatchCheckResponse, BatchCheckRow
from delphi_contracts.category import Category, CategoryScheme, SubcategoryId
from delphi_contracts.enums import NeighborDirection
from delphi_contracts.eval_run import EvalRun, EvalScores
from delphi_contracts.extraction import (
    CONSENT_DESTINATION,
    BibliographyEntry,
    Extraction,
    PdfUpload,
)
from delphi_contracts.graph import Edge, EdgeKind
from delphi_contracts.identity import Identity, IdentityKind
from delphi_contracts.llm import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    EmbedRequest,
    EmbedResponse,
    FakeProvider,
    LlmProvider,
    OpenAICompatibleProvider,
    ProviderKind,
    ProviderSettings,
    build_provider,
    cosine,
    hash_embed,
    provider_settings_from_env,
)
from delphi_contracts.neighborhood import Neighbor, Neighborhood, NeighborhoodMode
from delphi_contracts.openapi import build_openapi, openapi_path
from delphi_contracts.paths import (
    ContextLeakError,
    MaskedContext,
    PathKind,
    PathProposal,
    PathRequest,
)
from delphi_contracts.work import Work, WorkKind

__all__ = [
    "CONSENT_DESTINATION",
    "BatchCheckRequest",
    "BatchCheckResponse",
    "BatchCheckRow",
    "BibliographyEntry",
    "Category",
    "CategoryScheme",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ContextLeakError",
    "Edge",
    "EdgeKind",
    "EmbedRequest",
    "EmbedResponse",
    "EvalRun",
    "EvalScores",
    "Extraction",
    "FakeProvider",
    "Identity",
    "IdentityKind",
    "LlmProvider",
    "MaskedContext",
    "Neighbor",
    "NeighborDirection",
    "Neighborhood",
    "NeighborhoodMode",
    "OpenAICompatibleProvider",
    "PathKind",
    "PathProposal",
    "PathRequest",
    "PdfUpload",
    "ProviderKind",
    "ProviderSettings",
    "SubcategoryId",
    "Work",
    "WorkKind",
    "build_openapi",
    "build_provider",
    "cosine",
    "hash_embed",
    "openapi_path",
    "provider_settings_from_env",
]
