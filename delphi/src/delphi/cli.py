"""Command-line entry for the Delphi API."""

from __future__ import annotations

import argparse
import os

import uvicorn

from delphi.app import AppContainer, create_app
from delphi.postgres import catalog_from_url

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
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DELPHI_DATABASE_URL"),
        help="Postgres DSN; default memory catalog when unset",
    )
    args = parser.parse_args(argv)
    app = create_app(AppContainer(catalog=catalog_from_url(args.database_url)))
    uvicorn.run(app, host=args.host, port=args.port)
    return 0
