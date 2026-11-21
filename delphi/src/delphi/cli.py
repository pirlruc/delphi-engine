"""Command-line entry for the Delphi API."""

from __future__ import annotations

import argparse
import os

import uvicorn
from delphi_contracts.json_tree import namespace_dict

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
    raw = namespace_dict(parser.parse_args(argv))
    database_url = raw.get("database_url")
    host = raw.get("host")
    port = raw.get("port")
    app = create_app(
        AppContainer(
            catalog=catalog_from_url(
                database_url if isinstance(database_url, str) else None
            )
        )
    )
    uvicorn.run(
        app,
        host=host if isinstance(host, str) else "127.0.0.1",
        port=port if isinstance(port, int) and not isinstance(port, bool) else 8000,
    )
    return 0
