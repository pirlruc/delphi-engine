"""Delphi CLI tests."""

from delphi.cli import main


def test_main_invokes_uvicorn(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(app: object, host: str, port: int) -> None:
        captured["host"] = host
        captured["port"] = port
        captured["app"] = app

    monkeypatch.setattr("delphi.cli.uvicorn.run", fake_run)
    assert main(["--host", "0.0.0.0", "--port", "9000"]) == 0
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9000
    assert main(["--database-url", ""]) == 0
