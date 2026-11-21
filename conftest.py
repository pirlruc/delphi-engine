"""Put workspace sources ahead of the repository directory on ``sys.path``.

The member directories use the same names as their import packages. A root
pytest run would otherwise bind ``hermes`` to ``./hermes`` instead of
``./hermes/src/hermes``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    """Prefer each member's ``src`` tree over the repository root."""
    root = Path(__file__).resolve().parent
    for rel in (
        "contracts/src",
        "delphi/src",
        "daedalus/src",
        "prometheus/src",
        "epimetheus/src",
        "hermes/src",
    ):
        entry = str(root / rel)
        if entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)
    root_s = str(root)
    sys.path = [entry for entry in sys.path if entry not in {"", root_s}]
    for name in list(sys.modules):
        if name == "hermes" or name.startswith("hermes."):
            del sys.modules[name]
        if name in {"delphi", "daedalus", "epimetheus"} or name.startswith(
            ("delphi.", "daedalus.", "epimetheus.")
        ):
            del sys.modules[name]
