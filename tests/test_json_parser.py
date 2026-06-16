from datetime import datetime
from types import NoneType
from typing import Callable, Any

import pytest
from dateutil.tz import tzlocal

from TwitchChannelPointsMiner.JsonParser import (
    InvalidJsonShapeError,
    JsonParentContext,
    describe_value,
    dig,
    expect_dict,
    expect_int,
    expect_is_type,
    expect_iso_8601,
    expect_str,
    list_parser,
    optional_parser,
    parse_expected_value,
    parse_value,
)

test_json_parent_context_data = [
    ([], "inner message"),
    (["first"], "inner message 2"),
    (["first", 5, "third"], "inner message 3"),
]


@pytest.mark.parametrize("path,message", test_json_parent_context_data)
def test_json_parent_context(path: list[int | str], message: str):
    def test_inner(inner_path: list[int | str]):
        if len(inner_path) == 0:
            raise InvalidJsonShapeError(path=[], message=message)
        with JsonParentContext(inner_path[0]):
            return test_inner(inner_path[1:])

    try:
        test_inner(path)
    except InvalidJsonShapeError as e:
        assert repr(e) == repr(
            InvalidJsonShapeError(path=list(reversed(path)), message=message)
        )


class ExampleDataClass:
    def __init__(self, value1: str, value2: int):
        self.value1 = value1
        self.value2 = value2

    def __repr__(self) -> str:
        return f"value1={self.value1}, value2={self.value2}"


test_describe_value_data = [
    (None, "None"),
    ({}, "dict"),
    ({"key": "value"}, "dict"),
    ([], "list"),
    ([1, 2, 3], "list"),
    (
        ExampleDataClass(value1="some value", value2=-100),
        "type: 'ExampleDataClass', value: 'value1=some value, value2=-100'",
    ),
]


@pytest.mark.parametrize("value,expected", test_describe_value_data)
def test_describe_value(value, expected):
    assert describe_value(value) == expected


test_expect_is_type_data = [
    (None, NoneType, None),
    (None, str, InvalidJsonShapeError(path=[], message="str expected, got None")),
    (None, int, InvalidJsonShapeError(path=[], message="int expected, got None")),
    (None, dict, InvalidJsonShapeError(path=[], message="dict expected, got None")),
    (None, bool, InvalidJsonShapeError(path=[], message="bool expected, got None")),
    (False, bool, None),
    (True, bool, None),
    (
        False,
        dict,
        InvalidJsonShapeError(
            path=[], message="dict expected, got type: 'bool', value: 'False'"
        ),
    ),
    (
        True,
        list,
        InvalidJsonShapeError(
            path=[], message="list expected, got type: 'bool', value: 'True'"
        ),
    ),
    (
        False,
        str,
        InvalidJsonShapeError(
            path=[], message="str expected, got type: 'bool', value: 'False'"
        ),
    ),
    (False, int, None),
    (True, int, None),
    ("some string", str, None),
    (
        "some string",
        int,
        InvalidJsonShapeError(
            path=[], message="int expected, got type: 'str', value: 'some string'"
        ),
    ),
    (
        "some string",
        ExampleDataClass,
        InvalidJsonShapeError(
            path=[],
            message="ExampleDataClass expected, got type: 'str', value: 'some string'",
        ),
    ),
    (
        "some string",
        NoneType,
        InvalidJsonShapeError(
            path=[],
            message="NoneType expected, got type: 'str', value: 'some string'",
        ),
    ),
    (0, int, None),
    (
        0,
        NoneType,
        InvalidJsonShapeError(
            path=[], message="NoneType expected, got type: 'int', value: '0'"
        ),
    ),
    (
        345,
        dict,
        InvalidJsonShapeError(
            path=[], message="dict expected, got type: 'int', value: '345'"
        ),
    ),
    ({}, dict, None),
    ({"key": "value"}, dict, None),
    (
        {"key": "value"},
        NoneType,
        InvalidJsonShapeError(path=[], message="NoneType expected, got dict"),
    ),
    (
        {"key": "value"},
        int,
        InvalidJsonShapeError(path=[], message="int expected, got dict"),
    ),
    (
        {"key": "value"},
        str,
        InvalidJsonShapeError(path=[], message="str expected, got dict"),
    ),
    ([], list, None),
    ([1, 2, 3], list, None),
    (["value 1", 2, ExampleDataClass("a", 10)], list, None),
    (
        [],
        NoneType,
        InvalidJsonShapeError(path=[], message="NoneType expected, got list"),
    ),
    (
        [1, 2, 3],
        str,
        InvalidJsonShapeError(path=[], message="str expected, got list"),
    ),
    (
        [1, 2, 3],
        dict,
        InvalidJsonShapeError(path=[], message="dict expected, got list"),
    ),
]


@pytest.mark.parametrize("value,_type,exception", test_expect_is_type_data)
def test_expect_is_type(value, _type: type, exception: InvalidJsonShapeError | None):
    """Covers all the basic `expect_...` functions."""
    try:
        expect_is_type(value, _type)
    except InvalidJsonShapeError as e:
        assert exception is not None, "Exception not expected"
        assert repr(e) == repr(exception)
    else:
        assert exception is None, "Exception expected"


test_expect_iso_8601_data = [
    (
        None,
        InvalidJsonShapeError(path=[], message="str expected, got None"),
    ),
    (
        0,
        InvalidJsonShapeError(
            path=[], message="str expected, got type: 'int', value: '0'"
        ),
    ),
    (
        [],
        InvalidJsonShapeError(path=[], message="str expected, got list"),
    ),
    (
        "",
        InvalidJsonShapeError(path=[], message="time data '' does not match format"),
    ),
    (
        "wrong format",
        InvalidJsonShapeError(
            path=[], message="time data 'wrong format' does not match format"
        ),
    ),
    (
        "2026-06-09T09:18:10.364124475Z",
        datetime(
            year=2026,
            month=6,
            day=9,
            hour=9,
            minute=18,
            second=10,
            microsecond=364124,
            tzinfo=tzlocal(),
        ),
    ),
    (
        "2026-11-24T18:49:50.4216871Z",
        datetime(
            year=2026,
            month=11,
            day=24,
            hour=18,
            minute=49,
            second=50,
            microsecond=421687,
            tzinfo=tzlocal(),
        ),
    ),
]


@pytest.mark.parametrize("value,expected", test_expect_iso_8601_data)
def test_expect_iso_8601(value, expected: InvalidJsonShapeError | datetime):
    try:
        result = expect_iso_8601(value)
        assert result == expected
    except InvalidJsonShapeError as e:
        assert isinstance(expected, InvalidJsonShapeError), "Exception not expected"
        assert repr(e) == repr(expected)
    else:
        assert isinstance(expected, datetime), "Exception expected"


def mock_parser_none(_):
    return None


test_parse_expected_value_data = [
    (
        {},
        "",
        mock_parser_none,
        InvalidJsonShapeError(path=[""], message="value is not present"),
    ),
    (
        {},
        "key",
        mock_parser_none,
        InvalidJsonShapeError(path=["key"], message="value is not present"),
    ),
    (
        {"key": "value"},
        "another_key",
        mock_parser_none,
        InvalidJsonShapeError(path=["another_key"], message="value is not present"),
    ),
    ({"key": "value"}, "key", expect_str, "value"),
    ({"key": "value", "another_key": "another value"}, "key", expect_str, "value"),
    (
        {"key": "value", "another_key": "another value"},
        "another_key",
        expect_str,
        "another value",
    ),
    (
        {"key": "value", "another_key": 123},
        "another_key",
        expect_str,
        InvalidJsonShapeError(
            path=["another_key"], message="str expected, got type: 'int', value: '123'"
        ),
    ),
    (
        {"key": "value", "another_key": False},
        "another_key",
        expect_str,
        InvalidJsonShapeError(
            path=["another_key"],
            message="str expected, got type: 'bool', value: 'False'",
        ),
    ),
]


@pytest.mark.parametrize(
    "source,property_name,type_parser,expected", test_parse_expected_value_data
)
def test_parse_expected_value(
    source: dict, property_name: str, type_parser: Callable[[Any], Any], expected: Any
):
    try:
        result = parse_expected_value(source, property_name, type_parser)
        assert result == expected
    except InvalidJsonShapeError as e:
        assert isinstance(expected, InvalidJsonShapeError), "Exception not expected"
        assert repr(e) == repr(expected)
    else:
        assert not isinstance(expected, InvalidJsonShapeError), "Exception expected"


test_parse_value_data = [
    ({}, "", mock_parser_none, None, None),
    ({}, "key", mock_parser_none, "default", "default"),
    ({"key": "value"}, "another_key", mock_parser_none, 123, 123),
    ({"key": "value"}, "key", expect_str, "default", "value"),
    (
        {"key": "value", "another_key": "another value"},
        "key",
        expect_str,
        "default",
        "value",
    ),
    (
        {"key": "value", "another_key": "another value"},
        "another_key",
        expect_str,
        "default",
        "another value",
    ),
    (
        {"key": "value", "another_key": 123},
        "another_key",
        expect_str,
        None,
        InvalidJsonShapeError(
            path=["another_key"], message="str expected, got type: 'int', value: '123'"
        ),
    ),
    (
        {"key": "value", "another_key": False},
        "another_key",
        expect_str,
        None,
        InvalidJsonShapeError(
            path=["another_key"],
            message="str expected, got type: 'bool', value: 'False'",
        ),
    ),
]


@pytest.mark.parametrize(
    "source,property_name,type_parser,default,expected", test_parse_value_data
)
def test_parse_value(
    source: dict,
    property_name: str,
    type_parser: Callable[[Any], Any],
    default: Any,
    expected: Any,
):
    try:
        result = parse_value(source, property_name, type_parser, default)
        assert result == expected
    except InvalidJsonShapeError as e:
        assert isinstance(expected, InvalidJsonShapeError), "Exception not expected"
        assert repr(e) == repr(expected)
    else:
        assert not isinstance(expected, InvalidJsonShapeError), "Exception expected"


test_list_parser_data = [
    ([], mock_parser_none, []),
    ([None], mock_parser_none, [None]),
    ([1, 2, 3], mock_parser_none, [None, None, None]),
    ([1, 2, 3], expect_int, [1, 2, 3]),
    (
        [1, 2, 3],
        expect_str,
        InvalidJsonShapeError(
            path=[0], message="str expected, got type: 'int', value: '1'"
        ),
    ),
    (
        ["value", "another value", 3],
        expect_str,
        InvalidJsonShapeError(
            path=[2], message="str expected, got type: 'int', value: '3'"
        ),
    ),
]


@pytest.mark.parametrize("value,value_type_parser,expected", test_list_parser_data)
def test_list_parser(
    value: list,
    value_type_parser: Callable[[Any], Any],
    expected: list | InvalidJsonShapeError,
):
    parser = list_parser(value_type_parser)
    try:
        result = parser(value)
        assert result == expected
    except InvalidJsonShapeError as e:
        assert isinstance(expected, InvalidJsonShapeError), "Exception not expected"
        assert repr(e) == repr(expected)
    else:
        assert not isinstance(expected, InvalidJsonShapeError), "Exception expected"


test_optional_parser_data = [
    (None, mock_parser_none, None),
    (None, expect_str, None),
    (None, expect_dict, None),
    ("value", expect_str, "value"),
    (
        "value",
        expect_int,
        InvalidJsonShapeError(
            path=[], message="int expected, got type: 'str', value: 'value'"
        ),
    ),
    (
        123,
        expect_dict,
        InvalidJsonShapeError(
            path=[], message="dict expected, got type: 'int', value: '123'"
        ),
    ),
]


@pytest.mark.parametrize("value,value_type_parser,expected", test_optional_parser_data)
def test_optional_parser(value, value_type_parser: Callable[[Any], Any], expected: Any):
    parser = optional_parser(value_type_parser)
    try:
        result = parser(value)
        assert result == expected
    except InvalidJsonShapeError as e:
        assert isinstance(expected, InvalidJsonShapeError), "Exception not expected"
        assert repr(e) == repr(expected)
    else:
        assert not isinstance(expected, InvalidJsonShapeError), "Exception expected"


test_dig_data = [
    (None, [], mock_parser_none, None),
    (
        None,
        ["first"],
        mock_parser_none,
        InvalidJsonShapeError(path=[], message="dict expected, got None"),
    ),
    (
        None,
        [0],
        mock_parser_none,
        InvalidJsonShapeError(path=[], message="list expected, got None"),
    ),
    (
        {},
        ["first"],
        mock_parser_none,
        InvalidJsonShapeError(path=["first"], message="value is not present"),
    ),
    (
        [],
        [0],
        mock_parser_none,
        InvalidJsonShapeError(
            path=[0], message="Index 0 is out of list range (length 0)"
        ),
    ),
    ({"first": ["second"]}, ["first", 0], expect_str, "second"),
    (
        {"first": [{"key": None, "third": "some value"}, None]},
        ["first", 0, "third"],
        expect_str,
        "some value",
    ),
    (
        {"first": [{"key": None, "third": "some value"}, None]},
        ["first", 1, "third"],
        expect_str,
        InvalidJsonShapeError(path=[1, "first"], message="dict expected, got None"),
    ),
]


@pytest.mark.parametrize("value,path,and_then,expected", test_dig_data)
def test_dig(value, path, and_then: Callable[[Any], Any], expected: Any):
    try:
        result = dig(value, path, and_then)
        assert result == expected
    except InvalidJsonShapeError as e:
        assert isinstance(expected, InvalidJsonShapeError), "Exception not expected"
        assert repr(e) == repr(expected)
    else:
        assert not isinstance(expected, InvalidJsonShapeError), "Exception expected"
