"""Contracts unit tests."""

from collections.abc import Callable
from datetime import date
from typing import cast
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from delphi_contracts.batch import BatchCheckRequest, BatchCheckRow
from delphi_contracts.category import Category
from delphi_contracts.enums import (
    CategoryScheme,
    EdgeKind,
    IdentityKind,
    NeighborDirection,
    NeighborhoodMode,
    PathKind,
    ProviderKind,
    SubcategoryId,
    WorkKind,
)
from delphi_contracts.extraction import CONSENT_DESTINATION, PdfUpload
from delphi_contracts.graph import Edge
from delphi_contracts.identity import Identity, normalize_identity
from delphi_contracts.llm import (
    ChatMessage,
    ChatRequest,
    EmbedRequest,
    FakeProvider,
    ProviderSettings,
    build_provider,
    cosine,
    hash_embed,
    l2_normalize,
    provider_settings_from_env,
)
from delphi_contracts.mask import citation_descendants, dropped_ids
from delphi_contracts.neighborhood import Neighbor, Neighborhood
from delphi_contracts.openapi import build_openapi, openapi_path, write_openapi
from delphi_contracts.paths import MaskedContext, PathRequest
from delphi_contracts.work import Work


def _work(title: str, published: date) -> Work:
    return Work(
        id=uuid4(),
        kind=WorkKind.PAPER,
        title=title,
        published_on=published,
        identities=(Identity(kind=IdentityKind.DOI, value=f"10.1/{title}"),),
        categories=(
            Category(
                scheme=CategoryScheme.OPENALEX_TOPIC,
                code="two-d",
                label="2D codes",
                subcategory=SubcategoryId.TWO_D_CODES,
            ),
        ),
    )


def test_identity_rejects_empty_value() -> None:
    """Verify this behavior."""
    with pytest.raises(ValidationError):
        Identity(kind=IdentityKind.DOI, value="")


def test_identity_normalizes_doi_and_patent() -> None:
    """Verify this behavior."""
    doi = Identity(kind=IdentityKind.DOI, value="https://doi.org/10.1000/QR-2014")
    assert doi.value == "10.1000/qr-2014"
    patent = Identity(kind=IdentityKind.PATENT, value="US-1234567-A")
    assert patent.value == "US1234567A"
    arxiv = Identity(kind=IdentityKind.ARXIV, value="arXiv:1605.00000")
    assert arxiv.value == "1605.00000"
    hashed = Identity(kind=IdentityKind.CONTENT_HASH, value=" abc ")
    assert hashed.value == "abc"
    assert normalize_identity(IdentityKind.OPENALEX, " W1 ") == "W1"
    canonicalize = cast(Callable[[object], object], Identity._canonicalize)
    assert canonicalize("raw") == "raw"
    assert canonicalize({"kind": "nope", "value": "x"}) == {
        "kind": "nope",
        "value": "x",
    }
    assert canonicalize({"kind": "doi", "value": 12}) == {"kind": "doi", "value": 12}


def test_batch_check_request_requires_rows() -> None:
    """Verify this behavior."""
    with pytest.raises(ValidationError):
        BatchCheckRequest(identities=())


def test_batch_check_rejects_more_than_500_identities() -> None:
    """Verify this behavior."""
    identities = tuple(
        Identity(kind=IdentityKind.DOI, value=f"10.1/{index}") for index in range(501)
    )
    with pytest.raises(ValidationError):
        BatchCheckRequest(identities=identities)


def test_batch_check_row_unknown() -> None:
    """Verify this behavior."""
    identity = Identity(kind=IdentityKind.ARXIV, value="1605.00000")
    row = BatchCheckRow(identity=identity, known=False)
    assert row.work_id is None
    assert row.known is False


def test_pdf_upload_consent_constant() -> None:
    """Verify this behavior."""
    upload = PdfUpload(
        consent_destination=CONSENT_DESTINATION,
        filename="paper.pdf",
        content_hash="a" * 32,
    )
    assert upload.consent_destination == "delphi"


def test_path_request_kinds() -> None:
    """Verify this behavior."""
    request = PathRequest(
        kind=PathKind.PATENT_WHITESPACE,
        subcategory="two_d_codes",
        seed_work_id=uuid4(),
    )
    assert request.kind is PathKind.PATENT_WHITESPACE
    with pytest.raises(ValidationError):
        PathRequest(kind=PathKind.PATENT_WHITESPACE, subcategory="two_d_codes")


def test_masked_context_forbidden_ignores_absent_held_out() -> None:
    """Verify this behavior."""
    seed = _work("seed", date(2015, 1, 1))
    absent = uuid4()
    neighborhood = Neighborhood(seed=seed, mode=NeighborhoodMode.UNION, neighbors=())
    context = MaskedContext(
        seed=seed,
        mask_on=date(2016, 1, 1),
        held_out_ids=(absent,),
        neighborhood=neighborhood,
        subcategory="two_d_codes",
        kind=PathKind.RESEARCH_PATH,
    )
    assert absent not in context.forbidden_ids()


def test_masked_context_forbidden_includes_later_neighbors() -> None:
    """Verify this behavior."""
    seed = _work("seed", date(2015, 1, 1))
    later = _work("later", date(2018, 1, 1))
    neighborhood = Neighborhood(
        seed=seed,
        mode=NeighborhoodMode.UNION,
        neighbors=(
            Neighbor(
                work=later,
                edge_kind=EdgeKind.SIMILAR_TO,
                direction=NeighborDirection.OUT,
                score=0.9,
            ),
        ),
    )
    context = MaskedContext(
        seed=seed,
        mask_on=date(2016, 1, 1),
        held_out_ids=(later.id,),
        neighborhood=neighborhood,
        subcategory="two_d_codes",
        kind=PathKind.RESEARCH_PATH,
    )
    assert later.id in context.forbidden_ids()


def test_masked_context_same_day_neighbor_is_forbidden() -> None:
    """Verify this behavior."""
    seed = _work("seed", date(2015, 1, 1))
    sibling = _work("sibling", date(2016, 1, 1))
    neighborhood = Neighborhood(
        seed=seed,
        mode=NeighborhoodMode.UNION,
        neighbors=(
            Neighbor(
                work=sibling,
                edge_kind=EdgeKind.SIMILAR_TO,
                direction=NeighborDirection.OUT,
                score=0.5,
            ),
        ),
    )
    context = MaskedContext(
        seed=seed,
        mask_on=date(2016, 1, 1),
        held_out_ids=(),
        neighborhood=neighborhood,
        subcategory="two_d_codes",
        kind=PathKind.RESEARCH_PATH,
    )
    assert sibling.id in context.forbidden_ids()


def test_hash_embed_is_deterministic_and_normalized() -> None:
    """Verify this behavior."""
    left = hash_embed("qr data matrix barcode", dim=16)
    right = hash_embed("qr data matrix barcode", dim=16)
    assert left == right
    assert pytest.approx(sum(value * value for value in left), abs=1e-6) == 1.0


def test_cosine_clamps_and_matches_self() -> None:
    """Verify this behavior."""
    vector = hash_embed("steganography watermark")
    assert cosine(vector, vector) == pytest.approx(1.0)
    assert cosine(vector, tuple(-value for value in vector)) == 0.0
    scaled = tuple(value * 4 for value in vector)
    assert cosine(vector, scaled) == pytest.approx(1.0)
    assert cosine((1.0, 0.0), (1.0, 0.0, 0.0)) == 0.0
    zeros = (0.0, 0.0)
    assert l2_normalize(zeros) == zeros
    assert l2_normalize((3.0, 4.0)) == pytest.approx((0.6, 0.8))
    assert cosine(zeros, (1.0, 0.0)) == 0.0


def test_dropped_ids_includes_same_day_siblings() -> None:
    """Verify this behavior."""
    seed = _work("seed", date(2014, 1, 1))
    held = _work("held", date(2016, 3, 1))
    sibling = _work("sib", date(2016, 3, 1))
    citer = _work("citer", date(2016, 4, 1))
    edges = (Edge(from_work=citer.id, to_work=held.id, kind=EdgeKind.CITES),)
    dropped = dropped_ids(
        (seed, held, sibling, citer), edges, held.id, held.published_on
    )
    assert held.id in dropped
    assert sibling.id in dropped
    assert citer.id in dropped
    assert seed.id not in dropped
    assert citer.id in citation_descendants(held.id, edges)
    assert citation_descendants(uuid4(), edges) == frozenset()
    cycled = edges + (Edge(from_work=citer.id, to_work=citer.id, kind=EdgeKind.CITES),)
    assert citer.id in citation_descendants(held.id, cycled)


def test_hash_embed_empty_tokens_is_zero() -> None:
    """Verify this behavior."""
    vector = hash_embed("!!!", dim=8)
    assert vector == tuple(0.0 for _ in range(8))


def test_fake_provider_extract_generate_judge() -> None:
    """Verify this behavior."""
    provider = FakeProvider()
    extract = provider.chat(
        ChatRequest(
            messages=(
                ChatMessage(
                    role="user",
                    content=(
                        "Extract bibliographic metadata\n"
                        "Title: QR for widgets\n"
                        "Authors: Ada Lovelace, Alan Turing\n"
                        "Keywords: qr, barcode\n"
                        "1. Doe J. Prior art.\n"
                    ),
                ),
            )
        )
    )
    assert "QR for widgets" in extract.content
    numbered = provider.chat(
        ChatRequest(
            messages=(
                ChatMessage(
                    role="user",
                    content=(
                        "Extract bibliographic metadata\n"
                        "1. Kim. QR. doi:10.1000/qr-2014\n"
                    ),
                ),
            )
        )
    )
    assert "10.1000/qr-2014" in numbered.content
    generate = provider.chat(
        ChatRequest(
            messages=(
                ChatMessage(
                    role="system",
                    content="propose the next patent_whitespace",
                ),
                ChatMessage(
                    role="user", content="seed 123e4567-e89b-12d3-a456-426614174000"
                ),
            )
        )
    )
    assert "patent_whitespace" in generate.content
    judge = provider.chat(
        ChatRequest(
            messages=(ChatMessage(role="user", content="novelty llm-as-judge"),)
        )
    )
    assert "4" in judge.content
    embedded = provider.embed(EmbedRequest(text="qr codes"))
    assert embedded.provider is ProviderKind.FAKE
    assert len(embedded.vector) == 32


def test_provider_settings_from_env_defaults_and_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify this behavior."""
    fake = provider_settings_from_env({})
    assert fake.kind is ProviderKind.FAKE
    cloud = provider_settings_from_env({
        "DELPHI_LLM_KIND": "cloud",
        "DELPHI_LLM_API_KEY": "sk",
    })
    assert cloud.kind is ProviderKind.CLOUD
    assert cloud.api_key == "sk"
    local = provider_settings_from_env({
        "DELPHI_LLM_KIND": "local",
        "DELPHI_LLM_MODEL": "custom",
        "DELPHI_LLM_EMBEDDING_MODEL": "emb",
        "DELPHI_LLM_BASE_URL": "http://127.0.0.1:11434/v1",
    })
    assert local.base_url.startswith("http://127.0.0.1")
    assert local.model == "custom"
    with pytest.raises(ValueError, match="loopback"):
        provider_settings_from_env({
            "DELPHI_LLM_KIND": "local",
            "DELPHI_LLM_BASE_URL": "http://ollama/v1",
        })
    assert local.embedding_model == "emb"
    monkeypatch.setenv("DELPHI_LLM_KIND", "fake")
    assert provider_settings_from_env().kind is ProviderKind.FAKE
    provider = build_provider()
    assert provider.kind is ProviderKind.FAKE
    assert provider.model_id == "fake"


def test_openai_post_without_injected_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify this behavior."""
    captured: dict[str, object] = {}

    class _Response:
        def raise_for_status(self) -> None:
            """Verify this behavior."""
            return None

        def json(self) -> dict[str, object]:
            """Verify this behavior."""
            return {
                "model": "cloud",
                "choices": [{"message": {"content": "{}"}}],
            }

    def fake_post(
        url: str, json: dict[str, object], headers: dict[str, str], timeout: float
    ) -> _Response:
        """Verify this behavior."""
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("delphi_contracts.llm.httpx.post", fake_post)
    settings = ProviderSettings(kind=ProviderKind.CLOUD, model="gpt", api_key="")
    provider = build_provider(settings)
    result = provider.chat(
        ChatRequest(
            messages=(ChatMessage(role="user", content="hi"),),
            json_mode=False,
        )
    )
    assert result.provider is ProviderKind.CLOUD
    assert "response_format" not in captured["json"]  # type: ignore[operator]
    assert str(captured["url"]).endswith("/chat/completions")
    assert provider.model_id == "gpt"


def test_fake_chat_defaults_to_generate_and_untitled_extract() -> None:
    """Verify this behavior."""
    provider = FakeProvider()
    generate = provider.chat(
        ChatRequest(messages=(ChatMessage(role="user", content="hello"),))
    )
    assert "research_path" in generate.content
    extract = provider.chat(
        ChatRequest(
            messages=(
                ChatMessage(role="user", content="Extract bibliographic metadata only"),
            )
        )
    )
    assert "Untitled work" in extract.content


def test_eval_run_scores_round_trip() -> None:
    """Verify this behavior."""
    from delphi_contracts.eval_run import EvalRun, EvalScores

    run = EvalRun(
        id=uuid4(),
        held_out_id=uuid4(),
        seed_id=uuid4(),
        kind=PathKind.RESEARCH_PATH,
        subcategory="steganography",
        provider=ProviderKind.FAKE,
        model_id="fake",
        scores=EvalScores(novelty=3, relevance=4, accuracy=5, embedding_similarity=0.5),
    )
    assert run.scores.accuracy == 5


def test_context_leak_error_is_value_error() -> None:
    """Verify this behavior."""
    from delphi_contracts.paths import ContextLeakError

    with pytest.raises(ContextLeakError):
        raise ContextLeakError("future work")


def test_openai_compatible_chat_and_embed() -> None:
    """Verify this behavior."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(
                200,
                json={
                    "model": "local-model",
                    "choices": [{"message": {"content": '{"ok": true}'}}],
                },
            )
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.0, 1.0]}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    settings = ProviderSettings(
        kind=ProviderKind.LOCAL,
        model="local-model",
        embedding_model="local-embed",
        base_url="http://ollama.local/v1",
        api_key="sk-test",
    )
    provider = build_provider(settings, client=client)
    assert provider.model_id == "local-model"
    chat = provider.chat(
        ChatRequest(messages=(ChatMessage(role="user", content="hi"),))
    )
    assert chat.model == "local-model"
    embedded = provider.embed(EmbedRequest(text="hello"))
    assert embedded.vector == (0.0, 1.0)


def test_openai_handles_empty_payloads() -> None:
    """Verify this behavior."""

    def handler(_request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        return httpx.Response(200, json={"choices": [], "data": "nope"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = ProviderSettings(kind=ProviderKind.LOCAL, model="m", api_key="k")
    provider = build_provider(settings, client=client)
    chat = provider.chat(
        ChatRequest(messages=(ChatMessage(role="user", content="hi"),))
    )
    assert chat.content == "{}"
    embedded = provider.embed(EmbedRequest(text="hello"))
    assert embedded.vector == ()


def test_openapi_includes_required_paths_and_schemas(tmp_path) -> None:
    """Verify this behavior."""
    document = build_openapi()
    assert document["openapi"].startswith("3.")
    paths = document["paths"]
    assert "/v1/works:batch-check" in paths
    assert "/v1/works/{work_id}/neighborhood" in paths
    assert "/v1/uploads" in paths
    assert "/v1/generate" in paths
    schemas = document["components"]["schemas"]
    for name in (
        "Work",
        "BatchCheckRequest",
        "PdfUpload",
        "Extraction",
        "Neighborhood",
        "PathRequest",
        "EvalRun",
    ):
        assert name in schemas
    written = write_openapi(tmp_path / "openapi.json")
    assert written.is_file()
    assert openapi_path().name == "openapi.json"
