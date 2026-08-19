"""Command-line entry for the Delphi API."""

from __future__ import annotations

import argparse

import uvicorn

from delphi.app import AppContainer, create_app
from delphi.catalog import MemoryCatalog

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Run the prototype ASGI server.

    Args:
        argv: Optional CLI args.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Delphi prototype API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    app = create_app(AppContainer(catalog=MemoryCatalog()))
    uvicorn.run(app, host=args.host, port=args.port)
    return 0
