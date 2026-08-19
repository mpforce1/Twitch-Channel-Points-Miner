import threading
from time import sleep
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.utils.Utils import (
    interruptible_repeating_task,
    interruptible_sleep,
    ordinal,
    oxford_comma_list,
    truncate_url_path_query,
)

test_interruptible_sleep_uninterrupted_data = [
    [0, 0],
    [0, 1],
    [1, 0.5],
    [1, 0.1],
    [1, 1],
    [1, 2],
]


def return_true():
    return True


def return_false():
    return False


@pytest.mark.parametrize("duration,step", test_interruptible_sleep_uninterrupted_data)
def test_interruptible_sleep_uninterrupted(duration: float, step: float):
    uninterrupted = interruptible_sleep(return_true, duration, step)
    assert uninterrupted is True


test_interruptible_sleep_interrupted_data = [
    [0, 0],
    [0, 1],
    [1, 0.5],
    [1, 0.1],
    [1, 1],
    [1, 2],
]


@pytest.mark.parametrize("duration,step", test_interruptible_sleep_interrupted_data)
def test_interruptible_sleep_interrupted(duration: float, step: float):
    uninterrupted = interruptible_sleep(return_false, duration, step)
    assert uninterrupted is False


def test_interruptible_sleep():
    """
    Tests that sleep gets interrupted at the expected point.
    """
    run = MagicMock()
    run.side_effect = [True, True, True, False]
    # Mock returns True 3 times before returning False
    # so at 1 second intervals we should see the call count increment by 1
    # and the thread remain active, until the fourth call which should end the thread

    thread = threading.Thread(target=interruptible_sleep, args=(run, 5, 1))
    thread.start()
    sleep(0.5)
    run.assert_called_once()
    assert thread.is_alive() is True
    sleep(1)
    assert run.call_count == 2
    assert thread.is_alive() is True
    sleep(1)
    assert run.call_count == 3
    assert thread.is_alive() is True
    sleep(1)
    assert run.call_count == 4
    assert thread.is_alive() is False


def test_interruptible_repeating_task():
    task = MagicMock()

    run = MagicMock()
    run.side_effect = [True, True, True, False, False]

    period = 1

    step = 0.1

    thread = threading.Thread(
        target=interruptible_repeating_task,
        args=(task, run, return_false, period, step),
    )
    thread.start()

    # Called once in the sleep loop
    sleep(0.05)
    assert run.call_count == 1
    assert thread.is_alive() is True
    assert task.call_count == 0

    # Called an additional time in the sleep loop
    sleep(0.1)
    assert run.call_count == 2
    assert thread.is_alive() is True
    assert task.call_count == 0

    # Called an additional 2 times which should cause it to end early, the main loop will then check it again
    sleep(0.5)
    assert run.call_count == 5
    assert thread.is_alive() is False
    assert task.call_count == 0


def test_interruptible_repeating_task_execute_once():
    task = MagicMock()

    run = MagicMock()
    run.side_effect = [True, True, True, True, True, False, False]

    period = 1

    step = 0.5

    thread = threading.Thread(
        target=interruptible_repeating_task,
        args=(task, run, return_false, period, step),
    )
    thread.start()

    # Called once in the sleep loop
    sleep(0.05)
    assert run.call_count == 1
    assert thread.is_alive() is True
    assert task.call_count == 0

    # Same call count until 0.5 seconds
    sleep(0.4)
    assert run.call_count == 1
    assert thread.is_alive() is True
    assert task.call_count == 0

    # Called an additional time in the sleep loop
    sleep(0.1)
    assert run.call_count == 2
    assert thread.is_alive() is True
    assert task.call_count == 0

    # Called a final time when exiting the sleep loop, once in the main loop, and again after executing the task
    sleep(0.5)
    assert run.call_count == 5
    assert thread.is_alive() is True
    assert task.call_count == 1

    # No additional calls
    sleep(0.3)
    assert run.call_count == 5
    assert thread.is_alive() is True
    assert task.call_count == 1

    # Called again in sleep loop exiting early, and finally in the main loop
    sleep(0.2)
    assert run.call_count == 7
    assert thread.is_alive() is False
    assert task.call_count == 1


def test_interruptible_repeating_task_execute_twice():
    task = MagicMock()

    run = MagicMock()
    run.side_effect = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ]

    period = 0.5

    step = 0.3

    thread = threading.Thread(
        target=interruptible_repeating_task,
        args=(task, run, return_false, period, step),
    )
    thread.start()

    # Called once in the sleep loop
    sleep(0.05)
    assert run.call_count == 1
    assert thread.is_alive() is True
    assert task.call_count == 0

    # Called once more
    sleep(0.4)
    assert run.call_count == 2
    assert thread.is_alive() is True
    assert task.call_count == 0

    # Called a final time when exiting the sleep loop, once to verify the source, and again after executing the task
    sleep(0.1)
    assert run.call_count == 5
    assert thread.is_alive() is True
    assert task.call_count == 1

    # Called 3 times in the sleep loop, once to verify, and again after executing the task
    sleep(0.5)
    assert run.call_count == 9
    assert thread.is_alive() is True
    assert task.call_count == 2

    # Called again in sleep loop exiting early, and again to verify
    sleep(0.3)
    assert run.call_count == 11
    assert thread.is_alive() is False
    assert task.call_count == 2


test_oxford_comma_list_data = [
    [[], ""],
    [["item 1"], "item 1"],
    [["item 1", "item 2"], "item 1 and item 2"],
    [["item 1", "item 2", "item 3"], "item 1, item 2, and item 3"],
    [["item 1", "item 2", "item 3", "item 4"], "item 1, item 2, item 3, and item 4"],
]


@pytest.mark.parametrize("items,expected", test_oxford_comma_list_data)
def test_oxford_comma_list(items: list[str], expected: str) -> None:
    assert oxford_comma_list(items) == expected


test_ordinal_data = [
    (1, "1st"),
    (2, "2nd"),
    (3, "3rd"),
    (4, "4th"),
    (5, "5th"),
    (6, "6th"),
    (7, "7th"),
    (8, "8th"),
    (9, "9th"),
    (10, "10th"),
    (11, "11th"),
    (12, "12th"),
    (20, "20th"),
    (21, "21st"),
    (22, "22nd"),
    (23, "23rd"),
    (24, "24th"),
    (25, "25th"),
    (30, "30th"),
    (31, "31st"),
    (99, "99th"),
    (100, "100th"),
    (101, "101st"),
    (109, "109th"),
    (110, "110th"),
    (111, "111th"),
    (112, "112th"),
    (121, "121st"),
    (155, "155th"),
    (1234, "1234th"),
    (4321, "4321st"),
    (11111, "11111th"),
    (123456789, "123456789th"),
]


@pytest.mark.parametrize("value,expected", test_ordinal_data)
def test_ordinal(value, expected):
    assert ordinal(value) == expected


test_truncate_url_path_query_data = [
    # No path
    ("https://example.com/", 0, "https://example.com"),
    ("https://example.com/", 10, "https://example.com/"),
    # Some path
    ("https://example.com/path/segments/", 0, "https://example.com"),
    ("https://example.com/path/segments/", 5, "https://example.com/path"),
    ("https://example.com/path/segments/", 10, "https://example.com/path/segm"),
    # Query
    ("https://example.com/?param=arg&param=arg", 0, "https://example.com"),
    ("https://example.com/?param=arg&param=arg", 5, "https://example.com/?para"),
    ("https://example.com/?param=arg&param=arg", 10, "https://example.com/?param=arg"),
    # Path and query
    (
        "https://example.com/path/segments/?param=arg&param=arg",
        0,
        "https://example.com",
    ),
    (
        "https://example.com/path/segments/?param=arg&param=arg",
        5,
        "https://example.com/path",
    ),
    (
        "https://example.com/path/segments/?param=arg&param=arg",
        10,
        "https://example.com/path/segm",
    ),
]


@pytest.mark.parametrize("url,length,expected", test_truncate_url_path_query_data)
def test_truncate_url_path_query(url: str, length: int, expected: str):
    assert truncate_url_path_query(url, length) == expected
