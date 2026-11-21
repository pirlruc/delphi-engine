"""JSON boundary helpers."""

import json

import pytest

from delphi_contracts.json_tree import (
    as_dict,
    as_floats,
    as_list,
    as_str_list,
    is_object_dict,
    is_object_list,
    namespace_dict,
    parse_json,
    text_of,
)


def test_parse_json_reads_objects_and_rejects_text() -> None:
    """Check the behavior under test."""
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json(b"[1]") == [1]
    with pytest.raises(json.JSONDecodeError):
        parse_json("{")


def test_as_dict_keeps_string_keys() -> None:
    """Check the behavior under test."""
    assert as_dict({"a": 1, 2: "no"}) == {"a": 1}
    assert not as_dict([1])
    assert not as_dict("no")


def test_as_list_and_strings() -> None:
    """Check the behavior under test."""
    assert as_list([1, "a"]) == [1, "a"]
    assert not as_list("ab")
    assert not as_list({"a": 1})
    assert as_str_list(("a", 2)) == ["a", "2"]
    assert not as_str_list("ab")
    assert not as_str_list(None)


def test_as_floats_skips_non_numbers() -> None:
    """Check the behavior under test."""
    assert as_floats([1, 1.5, True, "x"]) == (1.0, 1.5)
    assert not as_floats("12")
    assert not as_floats(None)


def test_guards_match_dict_and_list() -> None:
    """Check the behavior under test."""
    assert is_object_dict({"a": 1})
    assert not is_object_dict([1])
    assert is_object_list([1])
    assert not is_object_list({"a": 1})
    assert not is_object_list("ab")


def test_namespace_dict_reads_attributes() -> None:
    """Check the behavior under test."""

    class _Box:
        def __init__(self) -> None:
            """Check the behavior under test."""
            self.flag = True
            self.name = "a"

    assert namespace_dict(_Box()) == {"flag": True, "name": "a"}
    assert not namespace_dict(object())


def test_text_of_skips_containers() -> None:
    """Check the behavior under test."""
    assert text_of("a") == "a"
    assert text_of(3) == "3"
    assert text_of(None) == ""
    assert text_of({"a": 1}) == ""
    assert text_of([1]) == ""
