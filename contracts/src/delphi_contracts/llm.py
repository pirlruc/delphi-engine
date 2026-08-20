"""SYS-006 LLM provider interface and adapters."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, ConfigDict, Field

from delphi_contracts.enums import ProviderKind

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "EmbedRequest",
    "EmbedResponse",
    "FakeProvider",
    "LlmProvider",
    "OpenAICompatibleProvider",
    "ProviderKind",
    "ProviderSettings",
    "build_provider",
    "cosine",
    "hash_embed",
    "l2_normalize",
    "provider_settings_from_env",
]

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TASK_HINTS: tuple[tuple[str, str], ...] = (
    ("extract bibliographic", "extract"),
    ("json extraction", "extract"),
    ("research_path", "generate"),
    ("patent_whitespace", "generate"),
    ("propose the next", "generate"),
    ("novelty", "judge"),
    ("llm-as-judge", "judge"),
)


class ChatMessage(BaseModel):
    """One chat turn.

    Attributes:
        role: system, user, or assistant.
        content: Message text.
    """

    model_config = ConfigDict(frozen=True)

    role: str
    content: str


class ChatRequest(BaseModel):
    """Provider-neutral chat call.

    Attributes:
        messages: Ordered turns.
        json_mode: When true, adapters ask for a JSON object.
    """

    model_config = ConfigDict(frozen=True)

    messages: tuple[ChatMessage, ...] = Field(min_length=1)
    json_mode: bool = True


class ChatResponse(BaseModel):
    """Chat completion text.

    Attributes:
        content: Assistant text (JSON when json_mode was set).
        model: Model id that produced the text.
        provider: Adapter that ran.
    """

    model_config = ConfigDict(frozen=True)

    content: str
    model: str
    provider: ProviderKind


class EmbedRequest(BaseModel):
    """Text to embed in the shared content-graph space.

    Attributes:
        text: Title+abstract or extracted body.
        model: Optional override of the configured embedding model.
    """

    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1)
    model: str | None = None


class EmbedResponse(BaseModel):
    """One embedding vector.

    Attributes:
        vector: Dense float components.
        model: Embedding model id.
        provider: Adapter that ran.
    """

    model_config = ConfigDict(frozen=True)

    vector: tuple[float, ...]
    model: str
    provider: ProviderKind


class ProviderSettings(BaseModel):
    """Config for build_provider.

    Attributes:
        kind: fake, cloud, or local.
        model: Chat model id.
        embedding_model: Embedding model id.
        base_url: OpenAI-compatible base URL.
        api_key: Bearer token; unused for fake.
        timeout_s: HTTP timeout for cloud/local.
        embed_dim: Fake hashing embed dimension.
    """

    model_config = ConfigDict(frozen=True)

    kind: ProviderKind = ProviderKind.FAKE
    model: str = "fake"
    embedding_model: str = "fake-hash"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    timeout_s: float = 30.0
    embed_dim: int = 32


def hash_embed(text: str, dim: int = 32) -> tuple[float, ...]:
    """Embed text as a normalized hashed bag-of-words vector.

    Args:
        text: Source text.
        dim: Vector length.

    Returns:
        Unit-length vector so cosine similarity is a dot product.
    """
    counts = [0.0] * dim
    for token in _TOKEN_RE.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        counts[index] += 1.0
    norm = math.sqrt(sum(value * value for value in counts))
    if norm == 0.0:
        return tuple(0.0 for _ in range(dim))
    return tuple(value / norm for value in counts)


def l2_normalize(vector: tuple[float, ...]) -> tuple[float, ...]:
    """Return a unit-length copy of ``vector``.

    Args:
        vector: Dense components.

    Returns:
        Normalized vector, or the original when the norm is zero.
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return tuple(value / norm for value in vector)


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    """Return cosine similarity of two vectors.

    Args:
        left: First vector.
        right: Second vector.

    Returns:
        Similarity in ``[0, 1]`` after clamping negatives to 0. Mismatched
        lengths score 0 so mixed embedding models cannot crash k-NN.
    """
    if len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    score = sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
    return max(0.0, min(1.0, score))


@runtime_checkable
class LlmProvider(Protocol):
    """Chat and embed surface shared by Fake, Cloud, and Local."""

    @property
    def kind(self) -> ProviderKind:
        """Return the adapter kind."""

    @property
    def model_id(self) -> str:
        """Return the chat model id."""

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Complete a chat request.

        Args:
            request: Messages and JSON mode flag.

        Returns:
            Assistant content.
        """

    def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Embed text for the content graph.

        Args:
            request: Source text.

        Returns:
            Dense vector in the shared space.
        """


class FakeProvider:
    """Deterministic adapter for tests and offline demos."""

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        """Store settings.

        Args:
            settings: Optional overrides; fake is the default kind.
        """
        self._settings = settings or ProviderSettings()

    @property
    def kind(self) -> ProviderKind:
        """Return fake."""
        return ProviderKind.FAKE

    @property
    def model_id(self) -> str:
        """Return the configured fake model id."""
        return self._settings.model

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Dispatch on prompt hints to extract, generate, or judge JSON.

        Args:
            request: Chat turns.

        Returns:
            JSON content matching the inferred task.
        """
        blob = "\n".join(message.content for message in request.messages)
        task = _task_for(blob)
        handlers = {
            "extract": _fake_extract,
            "generate": _fake_generate,
            "judge": _fake_judge,
        }
        content = handlers[task](blob)
        return ChatResponse(content=content, model=self.model_id, provider=self.kind)

    def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Return a hashed bag-of-words embedding.

        Args:
            request: Source text.

        Returns:
            Normalized vector.
        """
        vector = hash_embed(request.text, self._settings.embed_dim)
        model = request.model or self._settings.embedding_model
        return EmbedResponse(vector=vector, model=model, provider=self.kind)


class OpenAICompatibleProvider:
    """Cloud or local adapter talking to an OpenAI-compatible HTTP API."""

    def __init__(self, settings: ProviderSettings, client: httpx.Client | None = None) -> None:
        """Store settings and an optional injected client.

        Args:
            settings: Cloud or local configuration.
            client: Injected HTTP client for tests.
        """
        self._settings = settings
        self._client = client

    @property
    def kind(self) -> ProviderKind:
        """Return cloud or local from settings."""
        return self._settings.kind

    @property
    def model_id(self) -> str:
        """Return the configured chat model id."""
        return self._settings.model

    def chat(self, request: ChatRequest) -> ChatResponse:
        """POST /chat/completions.

        Args:
            request: Chat turns.

        Returns:
            First choice content.
        """
        payload: dict[str, object] = {
            "model": self._settings.model,
            "messages": [message.model_dump() for message in request.messages],
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self._post("/chat/completions", payload)
        choices = data.get("choices", [])
        first = choices[0] if isinstance(choices, list) and choices else {}
        raw_message = first.get("message") if isinstance(first, dict) else {}
        message = raw_message if isinstance(raw_message, dict) else {}
        content = str(message.get("content", "{}"))
        model = str(data.get("model", self._settings.model))
        return ChatResponse(content=content, model=model, provider=self.kind)

    def embed(self, request: EmbedRequest) -> EmbedResponse:
        """POST /embeddings.

        Args:
            request: Source text.

        Returns:
            First embedding vector.
        """
        model = request.model or self._settings.embedding_model
        payload: dict[str, object] = {"model": model, "input": request.text}
        data = self._post("/embeddings", payload)
        raw = data["data"]
        first = raw[0] if isinstance(raw, list) else {}
        embedding = first.get("embedding") if isinstance(first, dict) else []
        values = embedding if isinstance(embedding, list) else []
        vector = tuple(float(value) for value in values)
        return EmbedResponse(vector=vector, model=model, provider=self.kind)

    def _post(self, path: str, payload: dict[str, object]) -> dict[str, Any]:
        """POST JSON to the configured base URL.

        Args:
            path: Path under the base URL.
            payload: JSON body.

        Returns:
            Parsed JSON object.
        """
        headers = {"Content-Type": "application/json"}
        if self._settings.api_key:
            headers["Authorization"] = f"Bearer {self._settings.api_key}"
        url = f"{self._settings.base_url.rstrip('/')}{path}"
        if self._client is not None:
            response = self._client.post(url, json=payload, headers=headers)
        else:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._settings.timeout_s,
            )
        response.raise_for_status()
        parsed = response.json()
        return dict(parsed) if isinstance(parsed, dict) else {}


def provider_settings_from_env(environ: Mapping[str, str] | None = None) -> ProviderSettings:
    """Build provider settings from DELPHI_LLM_* environment variables.

    Args:
        environ: Mapping to read. Defaults to os.environ.

    Returns:
        Settings for build_provider. Missing vars keep Fake defaults.
    """
    env = os.environ if environ is None else environ
    raw_kind = env.get("DELPHI_LLM_KIND", ProviderKind.FAKE.value)
    kind = ProviderKind(raw_kind)
    defaults = {
        ProviderKind.FAKE: ("fake", "fake-hash", "https://api.openai.com/v1"),
        ProviderKind.CLOUD: ("gpt-4o-mini", "text-embedding-3-small", "https://api.openai.com/v1"),
        ProviderKind.LOCAL: ("llama3", "nomic-embed-text", "http://127.0.0.1:11434/v1"),
    }
    model, embedding, base = defaults[kind]
    return ProviderSettings(
        kind=kind,
        model=env.get("DELPHI_LLM_MODEL", model),
        embedding_model=env.get("DELPHI_LLM_EMBEDDING_MODEL", embedding),
        base_url=env.get("DELPHI_LLM_BASE_URL", base),
        api_key=env.get("DELPHI_LLM_API_KEY", ""),
    )


def build_provider(
    settings: ProviderSettings | None = None,
    client: httpx.Client | None = None,
) -> LlmProvider:
    """Construct the adapter selected by settings.kind.

    Args:
        settings: Adapter config. Defaults to Fake.
        client: Optional HTTP client for cloud/local tests.

    Returns:
        A provider implementing chat and embed.
    """
    resolved = settings or ProviderSettings()
    if resolved.kind is ProviderKind.FAKE:
        return FakeProvider(resolved)
    return OpenAICompatibleProvider(resolved, client=client)


def _task_for(blob: str) -> str:
    """Infer extract, generate, or judge from prompt text.

    Args:
        blob: Concatenated messages.

    Returns:
        Task key.
    """
    lowered = blob.lower()
    for needle, task in _TASK_HINTS:
        if needle in lowered:
            return task
    return "generate"


def _fake_extract(blob: str) -> str:
    """Parse Title/Authors/Keywords lines from the prompt.

    Args:
        blob: Prompt including PDF text.

    Returns:
        Extraction JSON.
    """
    title = _field(blob, "Title") or "Untitled work"
    authors = tuple(part.strip() for part in _field(blob, "Authors").split(",") if part.strip())
    keywords = tuple(part.strip() for part in _field(blob, "Keywords").split(",") if part.strip())
    body = blob
    return json.dumps({
        "title": title,
        "authors": authors,
        "keywords": keywords,
        "body_text": body,
        "bibliography": _bibliography(blob),
    })


def _fake_generate(blob: str) -> str:
    """Propose a path that cites UUIDs found in the prompt.

    Args:
        blob: Prompt including MaskedContext JSON.

    Returns:
        PathProposal list JSON.
    """
    ids = re.findall(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        blob,
        flags=re.IGNORECASE,
    )
    cited = ids[:3]
    kind = "patent_whitespace" if "patent_whitespace" in blob.lower() else "research_path"
    title = "Next step in the masked neighborhood"
    return json.dumps({
        "proposals": [
            {
                "kind": kind,
                "title": title,
                "claims": ["Extend techniques cited in the past-only neighborhood."],
                "rationale": "Generated from masked context only.",
                "cited_work_ids": cited,
                "rank": 1,
            }
        ]
    })


def _fake_judge(_blob: str) -> str:
    """Return mid-high deterministic judge scores.

    Args:
        _blob: Unused prompt.

    Returns:
        EvalScores JSON without embedding similarity.
    """
    return json.dumps({"novelty": 4, "relevance": 4, "accuracy": 4})


def _field(blob: str, label: str) -> str:
    """Return text after ``Label:`` on a line.

    Args:
        blob: Prompt text.
        label: Field name.

    Returns:
        Captured value or empty string.
    """
    match = re.search(rf"^{label}:\s*(.+)$", blob, flags=re.MULTILINE | re.IGNORECASE)
    if match is None:
        return ""
    return match.group(1).strip()


def _bibliography(blob: str) -> list[dict[str, str]]:
    """Collect numbered reference lines.

    Args:
        blob: Prompt text.

    Returns:
        Raw bibliography dicts.
    """
    rows: list[dict[str, str]] = []
    for match in re.finditer(r"^\s*\d+[.)]\s+(.+)$", blob, flags=re.MULTILINE):
        raw = match.group(1).strip()
        row = {"raw": raw}
        doi = re.search(r"10\.\d{4,}/[^\s]+", raw)
        if doi is not None:
            row["doi"] = doi.group(0).rstrip(".,;")
        rows.append(row)
    return rows
