"""Hermes CLI tests."""

from pathlib import Path
from uuid import uuid4

from delphi_contracts.enums import IdentityKind, NeighborhoodMode, PathKind
from delphi_contracts.identity import Identity
from typer.testing import CliRunner

from hermes.cache import ResultCache
from hermes.cli import app
from hermes.client import DelphiClient


class _Response:
    def __init__(self, payload: object, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self) -> object:
        return self._payload


class _Http:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def post(
        self, url: str, json: object = None, files: object = None, data: object = None
    ) -> _Response:
        self.calls.append(url)
        if url.endswith("batch-check"):
            return _Response({
                "rows": [
                    {
                        "identity": {"kind": "doi", "value": "10.1/x"},
                        "known": False,
                        "work_id": None,
                    }
                ]
            })
        if url.endswith("uploads"):
            return _Response({
                "extraction": {
                    "title": "Uploaded",
                    "authors": ["Ada"],
                    "keywords": ["qr"],
                    "bibliography": [
                        {"raw": "Prior", "matched_work_id": "11111111-1111-1111-1111-111111111111"}
                    ],
                },
                "neighborhood": {
                    "neighbors": [
                        {"edge_kind": "cites"},
                        {"edge_kind": "similar_to"},
                    ]
                },
            })
        if url.endswith("generate"):
            return _Response([{"title": "Next path", "kind": "research_path"}])
        return _Response({})

    def get(self, url: str, params: object = None) -> _Response:
        self.calls.append(url)
        return _Response({"seed": {"title": "QR 2014"}, "neighbors": []})

    def close(self) -> None:
        self.calls.append("close")


def test_cache_round_trip(tmp_path: Path) -> None:
    cache = ResultCache(tmp_path / "c.sqlite")
    cache.put("batch-check", {"ok": True})
    assert cache.get("batch-check") == {"ok": True}
    assert cache.get("missing") is None


def test_cli_refuses_upload_without_consent(tmp_path: Path) -> None:
    runner = CliRunner()
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF")
    result = runner.invoke(
        app,
        ["upload", str(pdf), "--subcategory", "two_d_codes"],
    )
    assert result.exit_code == 2


def test_cli_batch_check_and_neighborhood(monkeypatch, tmp_path: Path) -> None:
    http = _Http()
    monkeypatch.setattr(
        "hermes.cli.DelphiClient",
        lambda base_url: DelphiClient(base_url, client=http),
    )
    runner = CliRunner()
    cache = tmp_path / "h.sqlite"
    result = runner.invoke(
        app,
        [
            "batch-check",
            "--doi",
            "10.1/x",
            "--arxiv",
            "1605.00000",
            "--patent",
            "US-1",
            "--cache-path",
            str(cache),
        ],
    )
    assert result.exit_code == 0
    work_id = str(uuid4())
    neighborhood = runner.invoke(
        app,
        [
            "neighborhood",
            work_id,
            "--subcategory",
            "two_d_codes",
            "--mode",
            "union",
            "--cache-path",
            str(cache),
        ],
    )
    assert neighborhood.exit_code == 0


def test_cli_generate_and_upload(monkeypatch, tmp_path: Path) -> None:
    http = _Http()
    monkeypatch.setattr(
        "hermes.cli.DelphiClient",
        lambda base_url: DelphiClient(base_url, client=http),
    )
    runner = CliRunner()
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF")
    cache = tmp_path / "h.sqlite"
    uploaded = runner.invoke(
        app,
        [
            "upload",
            str(pdf),
            "--subcategory",
            "two_d_codes",
            "--consent-destination",
            "delphi",
            "--cache-path",
            str(cache),
        ],
    )
    assert uploaded.exit_code == 0
    generated = runner.invoke(
        app,
        [
            "generate",
            "research_path",
            "--subcategory",
            "two_d_codes",
            "--seed-work-id",
            str(uuid4()),
            "--cache-path",
            str(cache),
        ],
    )
    assert generated.exit_code == 0
    extracted = runner.invoke(
        app,
        [
            "generate",
            "research_path",
            "--subcategory",
            "two_d_codes",
            "--extraction-id",
            str(uuid4()),
            "--as-of",
            "2024-01-15",
            "--cache-path",
            str(cache),
        ],
    )
    assert extracted.exit_code == 0
    missing_seed = runner.invoke(
        app,
        ["generate", "research_path", "--subcategory", "two_d_codes"],
    )
    assert missing_seed.exit_code == 2
    bad_date = runner.invoke(
        app,
        [
            "generate",
            "research_path",
            "--subcategory",
            "two_d_codes",
            "--seed-work-id",
            str(uuid4()),
            "--as-of",
            "not-a-date",
        ],
    )
    assert bad_date.exit_code != 0
    reprinted = runner.invoke(app, ["reprint", "upload", "--cache-path", str(cache)])
    assert reprinted.exit_code == 0
    missing = runner.invoke(app, ["reprint", "nope", "--cache-path", str(cache)])
    assert missing.exit_code == 2


def test_print_helpers_non_objects(capsys) -> None:
    from hermes.cli import _print_neighborhood, _print_upload

    _print_upload("raw")
    _print_upload({"extraction": "nope"})
    _print_neighborhood("raw")
    captured = capsys.readouterr().out
    assert "raw" in captured
    assert "nope" in captured


def test_batch_check_requires_identifier() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["batch-check"])
    assert result.exit_code != 0
    runner = CliRunner()
    result = runner.invoke(app, ["batch-check"])
    assert result.exit_code != 0


def test_client_methods(monkeypatch, tmp_path: Path) -> None:
    http = _Http()
    client = DelphiClient("http://delphi.local", client=http)
    client.batch_check((Identity(kind=IdentityKind.DOI, value="10.1/x"),))
    client.neighborhood(uuid4(), NeighborhoodMode.CONTENT, "two_d_codes")
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF")
    client.upload(pdf, "delphi", "two_d_codes")
    client.generate(PathKind.PATENT_WHITESPACE, "two_d_codes", uuid4())
    client.generate(
        PathKind.RESEARCH_PATH,
        "two_d_codes",
        extraction_id=uuid4(),
        as_of="2024-01-15",
    )
    client.close()
    owned = DelphiClient("http://delphi.local", client=http)
    owned._owns_client = True
    owned.close()
