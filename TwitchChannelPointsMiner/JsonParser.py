import abc
import datetime
from typing import ContextManager, Any, Callable

import dateutil


class JsonParserError(abc.ABC, Exception):
    pass


class InvalidJsonShapeError(JsonParserError):
    """Raised when JSON has an unexpected shape."""

    def __init__(self, path: list[str | int], message: str):
        self.path = path
        """The path in the JSON to the unexpected value."""
        self.message = message
        """Information about the unexpected value."""

    def __str__(self):
        def render_path_item(item: int | str) -> str:
            if isinstance(item, int):
                return str(item)
            else:
                return f'"{item}"'

        return f'JSON at [{", ".join(map(render_path_item, reversed(self.path)))}] has an invalid shape: {self.message}'

    def __repr__(self):
        return str(self)


class JsonParentContext(ContextManager):
    """Context Manager that appends the parent name to InvalidJsonShapeErrors"""

    def __init__(self, name: str | int):
        self.name = name

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, InvalidJsonShapeError):
            exc_val.path.append(self.name)


def describe_value(value: Any) -> str:
    # Omit the types for None, dict, and list as the latter would be too much to print
    if value is None:
        return "None"

    if isinstance(value, dict):
        return "dict"

    if isinstance(value, list):
        return "list"

    # Avoid double quotes for strings
    value_repr = value if isinstance(value, str) else repr(value)

    return f"type: '{type(value).__name__}', value: '{value_repr}'"


def expect_is_type[T](value: Any, _type: type[T]) -> T:
    """
    Parser that checks that the value is a given type then returns it as that type.
    :param value: The value to check.
    :param _type: The expected type of the value.
    :return: The value as the given type.
    """
    if not isinstance(value, _type):
        raise InvalidJsonShapeError(
            [], f"{_type.__name__} expected, got {describe_value(value)}"
        )
    return value


def expect_any(value: Any) -> Any:
    """
    Parser that just returns the given value.
    """
    return value


def expect_dict(value: Any) -> dict:
    """
    Parser that checks that the value is a dict then returns it.
    :raises InvalidJsonShapeError: if the value is not a dict
    """
    return expect_is_type(value, dict)


def expect_list(value: Any) -> list:
    """
    Parser that checks that the value is a list then returns it.
    :raises InvalidJsonShapeError: if the value is not a list.
    """
    return expect_is_type(value, list)


def expect_str(value: Any) -> str:
    """
    Parser that checks that the value is a string then returns it.
    :raises InvalidJsonShapeError: if the value is not a string.
    """
    return expect_is_type(value, str)


def expect_int(value: Any) -> int:
    """
    Parser that checks that the value is an int then returns it.
    :raises InvalidJsonShapeError: if the value is not an int.
    """
    return expect_is_type(value, int)


def expect_float(value: Any) -> float:
    """
    Parser that checks that the value is a float then returns it.
    :raises InvalidJsonShapeError: if the value is not a float.
    """
    return expect_is_type(value, float)

def expect_numeric(value: Any) -> float | int:
    """
    Parser that checks that the value is numeric (float or int) and returns it.
    :raises InvalidJsonShapeError: if the value is not numeric.
    """
    try:
        return expect_is_type(value, int)
    except InvalidJsonShapeError:
        try:
            return expect_is_type(value, float)
        except InvalidJsonShapeError:
            raise InvalidJsonShapeError(
                [], f"int or float expected, got {describe_value(value)}"
            )

def expect_bool(value: Any) -> bool:
    """
    Parser that checks that the value is a bool then returns it.
    :raises InvalidJsonShapeError: if the value is not a bool.
    """
    return expect_is_type(value, bool)


def expect_iso_8601(value: Any) -> datetime.datetime:
    """
    Parser that checks that the value is a valid ISO8601 string and returns it as a datetime.
    :raises InvalidJsonShapeError: if the value is not a valid ISO8601 string.
    """
    value = expect_str(value)

    try:
        return dateutil.parser.parse(value)
    except ValueError:
        pass
    raise InvalidJsonShapeError([], f"time data '{value}' does not match format")


def expect_server_time(value) -> datetime.datetime:
    """
    Parser that expects an int that represents a posix timestamp.
    :raises
    """
    value = expect_numeric(value)
    try:
        return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
    except ValueError:
        pass
    raise InvalidJsonShapeError(
        [], f"time data '{value}' is not a valid POSIX timestamp"
    )


def parse_expected_value[T](
    source: dict, property_name: str, type_parser: Callable[[Any], T]
) -> T:
    """
    Parses a value, with the given property name, in the given dict, and parses it using the given parser.
    :param source: The parent object, containing the value to parse.
    :param property_name: The property name of the value to parse.
    :param type_parser: A parser for the type of the value.
    :return: The parsed value.
    :raises InvalidJsonShapeError: if the property is not in the dict or the value cannot be parsed.
    """
    if property_name not in source:
        raise InvalidJsonShapeError([property_name], "value is not present")
    with JsonParentContext(property_name):
        return type_parser(source[property_name])


def parse_value[T](
    source: dict,
    property_name: str,
    type_parser: Callable[[Any], T],
    default: T | None = None,
) -> T | None:
    """
    Parses a value, with the given property name, in the given dict, and parses it using the given parser. The property
    may not exist in the source, in which case we return the default value.
    :param source: The parent object, containing the value to parse.
    :param property_name: The property name of the value to parse.
    :param type_parser: A parser for the type of the value.
    :param default: The default value to return if the value cannot be found (defaults to None).
    :return: The parsed value or the default if the property cannot be found.
    """
    if property_name not in source:
        return default
    with JsonParentContext(property_name):
        return type_parser(source[property_name])


def list_parser[T](value_type_parser: Callable[[Any], T]) -> Callable[[Any], list[T]]:
    """
    Returns a parser function that parses a value as a list and each item in the list using the given parser.
    :param value_type_parser: The parser for each value in the list.
    :return: The list parser function.
    """

    def inner_parser(source: Any) -> list[T]:
        expect_list(source)

        for index, item in enumerate(source):
            with JsonParentContext(index):
                source[index] = value_type_parser(item)
        return source

    return inner_parser


def optional_parser[T](
    value_type_parser: Callable[[Any], T],
) -> Callable[[Any], T | None]:
    """
    Returns a parser function that parses a value as either None or using the given parser.
    :param value_type_parser: The parser for the type of the value.
    :return: The parser function.
    """

    def inner_parser(value: Any) -> T | None:
        if value is None:
            return None
        else:
            return value_type_parser(value)

    return inner_parser


def dig[T](value, path: list[str | int], and_then: Callable[[Any], T]) -> T:
    """
    Utility to "dig" down into a JSON structure using a list of property names.
    :param value: The root value.
    :param path: The path to find.
    :param and_then: What to do with the value once found.
    :return: The value at the end of the path.
    """
    if len(path) == 0:
        return and_then(value)
    index = path[0]
    if isinstance(index, str):
        value = expect_dict(value)
        next_value = parse_expected_value(value, index, expect_any)
    else:
        value = expect_list(value)
        if index < len(value):
            next_value = value[index]
        else:
            raise InvalidJsonShapeError(
                [index], f"Index {index} is out of list range (length {len(value)})"
            )
    with JsonParentContext(index):
        return dig(next_value, path[1:], and_then)
