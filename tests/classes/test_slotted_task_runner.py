import time
from concurrent import futures
from typing import Any
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    Slot,
    SlottedTaskRunnerThread,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip
from TwitchChannelPointsMiner.classes.gql.data.response.FilterableVideoTower import (
    VideoEdge,
)

test_has_free_slot_data = [
    # All unfilled
    ([None], True),
    ([None, None], True),
    ([None, None, None], True),
    # Some unfilled
    ([None, "a"], True),
    ([None, None, "a"], True),
    ([None, None, None, "a"], True),
    (["a", "b", None], True),
    (["a", None, "B"], True),
    # All filled
    (["a"], False),
    (["a", "b"], False),
    (["a", "b", "c"], False),
    (["a", "b", "c", "d"], False),
]


@pytest.mark.parametrize("slots,expected", test_has_free_slot_data)
def test_has_free_slot(slots, expected):
    runner = SlottedTaskRunnerThread(
        twitch=MagicMock(),
        max_concurrent=len(slots),
        loop_interval_seconds=1,
        name="Test",
    )
    runner._slots = slots

    assert runner.has_free_slot() == expected


streamer_a = Streamer("a", "a")
streamer_b = Streamer("b", "b")
streamer_c = Streamer("c", "c")

test_has_context_data = [
    # Basic string
    ([None], "a", False),
    (["a"], "a", True),
    ([None, None], "a", False),
    ([None, "a"], "a", True),
    # Streamer
    ([None, None, None], streamer_a, False),
    ([None, streamer_a, None], streamer_a, True),
    ([None, streamer_a, None], streamer_a, True),
    ([streamer_b, None, None], streamer_a, False),
    ([streamer_a, streamer_b, streamer_c], streamer_a, True),
    ([streamer_c, streamer_b, streamer_a], streamer_a, True),
]


@pytest.mark.parametrize("slots,context,expected", test_has_context_data)
def test_has_context(slots: list, context, expected):
    runner = SlottedTaskRunnerThread(
        twitch=MagicMock(),
        max_concurrent=len(slots),
        loop_interval_seconds=1,
        name="Test",
    )
    runner._slots = [
        Slot(
            context=slot,
            future=MagicMock(),
            start_time=0,
            timeout_seconds=0,
            on_complete=lambda c, r: None,
        )
        for slot in slots
    ]

    assert runner.has_context(context) == expected


class SlotConfig:
    def __init__(
        self,
        context: str,
        done,
        result,
        start_time,
        timeout_seconds,
        expect_timeout: bool = False,
    ) -> None:
        self.context = context
        self.done = done
        self.result = result
        self.start_time = start_time
        self.timeout_seconds = timeout_seconds
        self.expect_timeout = expect_timeout

    def as_magic_mock(self):
        mock = MagicMock()
        mock.context = self.context
        mock.future = MagicMock()
        mock.future.done.return_value = self.done
        mock.future.result.return_value = self.result
        mock.start_time = self.start_time
        mock.timeout_seconds = self.timeout_seconds
        return mock


# MagicMock.fn.side_effect doesn't work for properties, work around by with a manual mock using @property
class MockTwitch:
    def __init__(self, clip: bool, running: bool, vod: bool, running_2: bool):
        self.clip = clip
        self._running = [running, running_2]
        self._running_index = 0
        self.vod = vod
        self.running_2 = running_2

    @property
    def running(self):
        if self._running_index >= len(self._running):
            return False
        value = self._running[self._running_index]
        self._running_index += 1
        return value

    def simulate_clip_playback(
        self, streamer, clip: Clip, max_watch_seconds: float, done  # pyright: ignore
    ):
        return self.clip

    def simulate_vod_playback(
        self,
        streamer,
        vod: VideoEdge,
        max_watch_seconds: float,
        done,  # pyright: ignore
    ):
        return self.vod


test_manage_slots_data = [
    # Minimum empty slots
    ([None, None], 0),
    # First slot filled but unfinished
    ([SlotConfig("a", False, None, 0, 20), None], 10),
    # Second slot filled but unfinished
    ([None, SlotConfig("a", False, None, 0, 20)], 10),
    # First slot finished, second unfinished
    (
        [
            SlotConfig("a", True, "a done", 0, 20),
            SlotConfig("b", False, None, 0, 20),
        ],
        10,
    ),
    # First slot unfinished, second finished
    (
        [
            SlotConfig("a", False, None, 0, 20),
            SlotConfig("b", True, "b done", 0, 20),
        ],
        10,
    ),
    # Both done
    (
        [
            SlotConfig("a", True, "a done", 0, 20),
            SlotConfig("b", True, "b done", 0, 20),
        ],
        10,
    ),
    # Timeouts
    # Second slot timed out, first unfinished
    (
        [
            SlotConfig("a", False, None, 10, 100, False),
            SlotConfig("b", False, None, 9, 100, True),
        ],
        110,
    ),
    #
    (
        [
            SlotConfig("a", False, None, 0, 100, True),
            SlotConfig("b", False, None, 1, 100, True),
            SlotConfig("c", False, None, 2, 100, False),
            SlotConfig("d", False, None, 3, 100, False),
            SlotConfig("e", False, None, 4, 100, False),
        ],
        102,
    ),
]


@pytest.mark.parametrize(
    "slots,current_time",
    test_manage_slots_data,
)
def test_manage_slots(slots: list[SlotConfig | None], current_time):
    twitch: Any = MockTwitch(clip=False, running=True, vod=False, running_2=False)
    runner = SlottedTaskRunnerThread(
        twitch=twitch, max_concurrent=len(slots), loop_interval_seconds=0, name="Test"
    )

    mock_slots = [slot.as_magic_mock() if slot is not None else None for slot in slots]
    runner._slots = list(mock_slots)

    as_completed = MagicMock()

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(time, "monotonic", lambda: current_time)
        patcher.setattr(futures, "as_completed", as_completed)
        runner.manage_slots()

    for index in range(len(slots)):
        slot = slots[index]
        mock_slot = mock_slots[index]
        if slot is not None and mock_slot is not None:
            # We check if it's done once
            mock_slot.future.done.assert_called_once()
            if slot.done:
                # If it's done the slot should be cleared
                assert runner._slots[index] is None
            if slot.expect_timeout:
                call_found = False
                for call in as_completed.call_args_list:
                    if (
                        call.args[0][0] == mock_slot.future
                        and call.kwargs["timeout"] == 0
                    ):
                        call_found = True
                        break
                assert call_found
