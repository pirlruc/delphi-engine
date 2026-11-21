"""Parse JSON without letting ``Any`` spread through the workspace.

``json.loads`` and ``dict`` / ``list`` narrowing both produce ``Any``.
Callers use the ``object`` values returned here. The ``Any`` stays in this
module so the workspace mypy floors stay measurable.
"""

from __future__ import annotations

import json
from typing import TypeGuard

__all__ = [
    "as_dict",
    "as_floats",
    "as_list",
    "as_str_list",
    "is_object_dict",
    "is_object_list",
    "namespace_dict",
    "parse_json",
    "text_of",
]


def is_object_dict(value: object) -> TypeGuard[dict[str, object]]:
    """Return whether ``value`` is a dict.

    Args:
        value: Candidate JSON value.

    Returns:
        True when ``value`` is a dict. Keys are treated as strings.
    """
    return isinstance(value, dict)


def is_object_list(value: object) -> TypeGuard[list[object]]:
    """Return whether ``value`` is a list.

    Args:
        value: Candidate JSON value.

    Returns:
        True when ``value`` is a list.
    """
    return isinstance(value, list)


def parse_json(data: str | bytes) -> object:
    """Parse a JSON document.

    Args:
        data: UTF-8 JSON text or bytes.

    Returns:
        The decoded document.

    Raises:
        json.JSONDecodeError: When ``data`` is not JSON.
    """
    return json.loads(data)


def as_dict(value: object) -> dict[str, object]:
    """Copy a JSON object.

    Args:
        value: Candidate object.

    Returns:
        String-keyed mapping. Empty when ``value`` is not a dict.
    """
    if not isinstance(value, dict):
        return {}
    copied: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(key, str):
            copied[key] = item
    return copied


def as_list(value: object) -> list[object]:
    """Copy a JSON array.

    Args:
        value: Candidate array. Strings are not treated as sequences.

    Returns:
        Element list. Empty when ``value`` is not a list.
    """
    if not isinstance(value, list):
        return []
    copied: list[object] = []
    for item in value:
        copied.append(item)
    return copied


def as_str_list(value: object) -> list[str]:
    """Copy a list or tuple of values as strings.

    Args:
        value: Candidate sequence. Strings are not split.

    Returns:
        String elements. Empty when ``value`` is not a list or tuple.
    """
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return []
    texts: list[str] = []
    for item in value:
        texts.append(str(item))
    return texts


def as_floats(value: object) -> tuple[float, ...]:
    """Copy a numeric sequence.

    Args:
        value: Candidate list or tuple of numbers.

    Returns:
        Floats. Empty when ``value`` is not a sequence of numbers.
    """
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return ()
    numbers: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            continue
        numbers.append(float(item))
    return tuple(numbers)


def namespace_dict(namespace: object) -> dict[str, object]:
    """Copy an argparse namespace into a string-keyed mapping.

    Args:
        namespace: Object with a ``__dict__``, usually ``argparse.Namespace``.

    Returns:
        Flag values. Empty when ``namespace`` has no ``__dict__``.
    """
    try:
        raw = vars(namespace)
    except TypeError:
        return {}
    copied: dict[str, object] = {}
    for key, item in raw.items():
        if isinstance(key, str):
            copied[key] = item
    return copied


def text_of(value: object) -> str:
    """Stringify a JSON leaf.

    Args:
        value: Scalar, or a container that has no text.

    Returns:
        Text. Empty for ``None``, objects, and arrays.
    """
    if value is None or isinstance(value, (dict, list)):
        return ""
    return str(value)
