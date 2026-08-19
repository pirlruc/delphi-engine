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
                },
                "neighborhood": {"neighbors": []},
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
        ["batch-check", "--doi", "10.1/x", "--arxiv", "1605.00000", "--cache-path", str(cache)],
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


def test_batch_check_requires_identifier() -> None:
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
    client.close()
    owned = DelphiClient("http://delphi.local", client=http)
    owned._owns_client = True
    owned.close()
