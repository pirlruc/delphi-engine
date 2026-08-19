"""Daedalus CLI: ingest the fixture slice."""

from __future__ import annotations

import argparse
from pathlib import Path

from daedalus.ingest import load_fixture

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args.

    Args:
        argv: Optional CLI args.

    Returns:
        Exit code. Fixture ingest without a live catalog prints the count.
    """
    parser = argparse.ArgumentParser(description="Daedalus ingest")
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    records = load_fixture(args.fixture)
    if args.dry_run:
        print(len(records))
        return 0
    print(len(records))
    return 0
