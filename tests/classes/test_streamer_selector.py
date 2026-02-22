import datetime
import time
from typing import Sequence, Callable
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.Settings import Priority, StreamerSource
from TwitchChannelPointsMiner.classes.StreamerSelector import (
    PriorityGroupSelector,
    PrioritySelector,
    priority_drops,
    priority_order,
    priority_points_ascending,
    priority_points_descending,
    priority_streak,
    priority_subscribed,
    NestedSelector,
    StreamerSelector,
    priority_streak_by_earliest_stream_created_at,
)
from TwitchChannelPointsMiner.classes.entities.Stream import Stream
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    Streamer,
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.gql import Properties

priority_order_data = [
    [[], 0, []],
    [[], 1, []],
    [[], 2, []],
    [[Streamer("1", "a")], 0, []],
    [[Streamer("1", "a")], 1, ["a"]],
    [[Streamer("1", "a")], 2, ["a"]],
    [[Streamer("1", "a"), Streamer("2", "b")], 0, []],
    [[Streamer("1", "a"), Streamer("2", "b")], 1, ["a"]],
    [[Streamer("1", "a"), Streamer("2", "b")], 2, ["a", "b"]],
    [[Streamer("1", "a"), Streamer("2", "b")], 3, ["a", "b"]],
]


@pytest.mark.parametrize("streamers,max_amount,expected_ids", priority_order_data)
def test_priority_order(
    streamers: list[Streamer], max_amount: int, expected_ids: list[str]
):
    streamer_ids = priority_order(streamers, max_amount)
    assert streamer_ids == expected_ids


priority_points_ascending_data = [
    [[], 0, []],
    [[], 1, []],
    [[], 2, []],
    [[Streamer("1", "a", 0)], 0, []],
    [[Streamer("1", "a", 0)], 1, ["a"]],
    [[Streamer("1", "a", 0)], 2, ["a"]],
    [[Streamer("1", "a", 0), Streamer("2", "b", 1)], 1, ["a"]],
    [[Streamer("1", "a", 0), Streamer("2", "b", 1)], 2, ["a", "b"]],
    [[Streamer("1", "a", 0), Streamer("2", "b", 1)], 3, ["a", "b"]],
    [[Streamer("1", "a", 1), Streamer("2", "b", 0)], 1, ["b"]],
    [[Streamer("1", "a", 1), Streamer("2", "b", 0)], 2, ["b", "a"]],
    [[Streamer("1", "a", 1), Streamer("2", "b", 0)], 3, ["b", "a"]],
    [[Streamer("1", "a", 0), Streamer("2", "b", 1), Streamer("3", "c", 2)], 1, ["a"]],
    [
        [Streamer("1", "a", 0), Streamer("2", "b", 1), Streamer("3", "c", 2)],
        2,
        ["a", "b"],
    ],
    [
        [Streamer("1", "a", 0), Streamer("2", "b", 1), Streamer("3", "c", 2)],
        3,
        ["a", "b", "c"],
    ],
    [
        [Streamer("1", "a", 0), Streamer("2", "b", 1), Streamer("3", "c", 2)],
        4,
        ["a", "b", "c"],
    ],
    [[Streamer("1", "a", 2), Streamer("2", "b", 1), Streamer("3", "c", 0)], 1, ["c"]],
    [
        [Streamer("1", "a", 2), Streamer("2", "b", 1), Streamer("3", "c", 0)],
        2,
        ["c", "b"],
    ],
    [
        [Streamer("1", "a", 2), Streamer("2", "b", 1), Streamer("3", "c", 0)],
        3,
        ["c", "b", "a"],
    ],
    [
        [Streamer("1", "a", 2), Streamer("2", "b", 1), Streamer("3", "c", 0)],
        4,
        ["c", "b", "a"],
    ],
]


@pytest.mark.parametrize(
    "streamers,max_amount,expected_ids", priority_points_ascending_data
)
def test_priority_points_ascending(
    streamers: list[Streamer], max_amount: int, expected_ids: list[str]
):
    streamer_ids = priority_points_ascending(streamers, max_amount)
    assert streamer_ids == expected_ids


priority_points_descending_data = [
    [[], 0, []],
    [[], 1, []],
    [[], 2, []],
    [[Streamer("1", "a", 0)], 0, []],
    [[Streamer("1", "a", 0)], 1, ["a"]],
    [[Streamer("1", "a", 0)], 2, ["a"]],
    [[Streamer("1", "a", 0), Streamer("2", "b", 1)], 1, ["b"]],
    [[Streamer("1", "a", 0), Streamer("2", "b", 1)], 2, ["b", "a"]],
    [[Streamer("1", "a", 0), Streamer("2", "b", 1)], 3, ["b", "a"]],
    [[Streamer("1", "a", 1), Streamer("2", "b", 0)], 1, ["a"]],
    [[Streamer("1", "a", 1), Streamer("2", "b", 0)], 2, ["a", "b"]],
    [[Streamer("1", "a", 1), Streamer("2", "b", 0)], 3, ["a", "b"]],
    [[Streamer("1", "a", 0), Streamer("2", "b", 1), Streamer("3", "c", 2)], 1, ["c"]],
    [
        [Streamer("1", "a", 0), Streamer("2", "b", 1), Streamer("3", "c", 2)],
        2,
        ["c", "b"],
    ],
    [
        [Streamer("1", "a", 0), Streamer("2", "b", 1), Streamer("3", "c", 2)],
        3,
        ["c", "b", "a"],
    ],
    [
        [Streamer("1", "a", 0), Streamer("2", "b", 1), Streamer("3", "c", 2)],
        4,
        ["c", "b", "a"],
    ],
    [[Streamer("1", "a", 2), Streamer("2", "b", 1), Streamer("3", "c", 0)], 1, ["a"]],
    [
        [Streamer("1", "a", 2), Streamer("2", "b", 1), Streamer("3", "c", 0)],
        2,
        ["a", "b"],
    ],
    [
        [Streamer("1", "a", 2), Streamer("2", "b", 1), Streamer("3", "c", 0)],
        3,
        ["a", "b", "c"],
    ],
    [
        [Streamer("1", "a", 2), Streamer("2", "b", 1), Streamer("3", "c", 0)],
        4,
        ["a", "b", "c"],
    ],
]


@pytest.mark.parametrize(
    "streamers,max_amount,expected_ids", priority_points_descending_data
)
def test_priority_points_descending(
    streamers: list[Streamer], max_amount: int, expected_ids: list[str]
):
    streamer_ids = priority_points_descending(streamers, max_amount)
    assert streamer_ids == expected_ids


settings_watch_streak_true = StreamerSettings(watch_streak=True)
settings_watch_streak_false = StreamerSettings(watch_streak=False)

stream_watch_streak_missing = Stream()
stream_watch_streak_missing.watch_streak_missing = True
stream_watch_streak_exists = Stream()
stream_watch_streak_exists.watch_streak_missing = False

stream_minute_watched_0 = Stream()
stream_minute_watched_0.minute_watched = 0
stream_minute_watched_3 = Stream()
stream_minute_watched_3.minute_watched = 3
stream_minute_watched_7 = Stream()
stream_minute_watched_7.minute_watched = 7
stream_minute_watched_10 = Stream()
stream_minute_watched_10.minute_watched = 10


def minutes_ago(mins: float):
    return time.time() - (mins * 60)


priority_streak_data = [
    [[], 0, []],
    [[], 1, []],
    [[], 2, []],
    # 1 Streamer, 0-2 max_amount, True/False settings.watch_streak
    [[Streamer("1", "a", settings=settings_watch_streak_true)], 0, []],
    [[Streamer("1", "a", settings=settings_watch_streak_true)], 1, ["a"]],
    [[Streamer("1", "a", settings=settings_watch_streak_false)], 1, []],
    [[Streamer("1", "a", settings=settings_watch_streak_true)], 2, ["a"]],
    [[Streamer("1", "a", settings=settings_watch_streak_false)], 2, []],
    # 1 Streamer, 0-2 max_amount, True settings.watch_streak, True/False watch streak missing
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
            )
        ],
        0,
        [],
    ],
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_exists,
            )
        ],
        0,
        [],
    ],
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
            )
        ],
        1,
        ["a"],
    ],
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_exists,
            )
        ],
        1,
        [],
    ],
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
            )
        ],
        2,
        ["a"],
    ],
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_exists,
            )
        ],
        2,
        [],
    ],
    # 1 Streamer, 0-2 max_amount, True settings.watch_streak, True watch streak missing, varying offline at
    # offline_at 0, 0 max_amount
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
                offline_at=0,
            )
        ],
        0,
        [],
    ],
    # offline_at 0, 1 max_amount
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
                offline_at=0,
            )
        ],
        1,
        ["a"],
    ],
    #   offline_at now
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
                offline_at=time.time(),
            )
        ],
        2,
        [],
    ],
    #   offline_at 25 minutes ago
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
                offline_at=minutes_ago(25),
            )
        ],
        2,
        [],
    ],
    #   offline_at 30 minutes ago
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
                offline_at=minutes_ago(30),
            )
        ],
        2,
        [],
    ],
    #   offline_at 35 minutes ago
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
                offline_at=minutes_ago(35),
            )
        ],
        2,
        ["a"],
    ],
    # 1 Streamer, 2 max_amount, True settings.watch_streak, True watch streak missing, offline_at 0, varying minute_watched
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_0,
                offline_at=0,
            )
        ],
        2,
        ["a"],
    ],
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_3,
                offline_at=0,
            )
        ],
        2,
        ["a"],
    ],
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_7,
                offline_at=0,
            )
        ],
        2,
        ["a"],
    ],
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_10,
                offline_at=0,
            )
        ],
        2,
        ["a"],
    ],
    # Multiple streamers in varying configurations
    #   4 streamers: 10 minutes watched, settings.watch_streak False, offline_at 30 mins ago, should succeed
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_10,
                offline_at=0,
            ),
            Streamer(
                "2",
                "b",
                settings=settings_watch_streak_false,
                stream=stream_minute_watched_0,
                offline_at=0,
            ),
            Streamer(
                "3",
                "c",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_0,
                offline_at=minutes_ago(30),
            ),
            Streamer(
                "4",
                "d",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_0,
                offline_at=minutes_ago(35),
            ),
        ],
        2,
        ["a", "d"],
    ],
    #   4 streamers: all valid
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_0,
                offline_at=0,
            ),
            Streamer(
                "2",
                "b",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_3,
                offline_at=0,
            ),
            Streamer(
                "3",
                "c",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_7,
                offline_at=minutes_ago(35),
            ),
            Streamer(
                "4",
                "d",
                settings=settings_watch_streak_true,
                stream=stream_minute_watched_0,
                offline_at=minutes_ago(60),
            ),
        ],
        2,
        ["a", "b"],
    ],
    # 4 streamers:
    #   4 streamers: 10 minutes watched, settings.watch_streak False, offline_at 30 mins ago, should succeed
    [
        [
            Streamer(
                "1",
                "a",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_exists,
                offline_at=0,
            ),
            Streamer(
                "2",
                "b",
                settings=settings_watch_streak_false,
                stream=stream_watch_streak_exists,
                offline_at=0,
            ),
            Streamer(
                "3",
                "c",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
                offline_at=minutes_ago(60),
            ),
            Streamer(
                "4",
                "d",
                settings=settings_watch_streak_true,
                stream=stream_watch_streak_missing,
                offline_at=minutes_ago(120),
            ),
        ],
        2,
        ["c", "d"],
    ],
]


@pytest.mark.parametrize("streamers,max_amount,expected_ids", priority_streak_data)
def test_priority_streak(
    streamers: list[Streamer], max_amount: int, expected_ids: list[str]
):
    streamer_ids = priority_streak(streamers, max_amount)
    assert streamer_ids == expected_ids


# TODO implement once the drops system is no longer broken
priority_drops_data = []


@pytest.mark.parametrize("streamers,max_amount,expected_ids", priority_drops_data)
def test_priority_drops(
    streamers: list[Streamer], max_amount: int, expected_ids: list[str]
):
    streamer_ids = priority_drops(streamers, max_amount)
    assert streamer_ids == expected_ids


priority_subscribed_data = [
    [[], 0, []],
    [[], 1, []],
    [[], 2, []],
    [[Streamer("1", "a", active_multipliers=[])], 0, []],
    [[Streamer("1", "a", active_multipliers=[Properties.Multiplier(0.2)])], 0, []],
    [[Streamer("1", "a", active_multipliers=[])], 1, []],
    [[Streamer("1", "a", active_multipliers=[Properties.Multiplier(0.2)])], 1, ["a"]],
    [
        [
            Streamer("1", "a", active_multipliers=[]),
            Streamer("2", "b", active_multipliers=[Properties.Multiplier(0.4)]),
        ],
        1,
        ["b"],
    ],
    [
        [
            Streamer("1", "a", active_multipliers=[]),
            Streamer("2", "b", active_multipliers=[Properties.Multiplier(0.4)]),
        ],
        1,
        ["b"],
    ],
    [
        [
            Streamer("1", "a", active_multipliers=[Properties.Multiplier(0.4)]),
            Streamer("2", "b", active_multipliers=[Properties.Multiplier(0.2)]),
        ],
        1,
        ["a"],
    ],
    [
        [
            Streamer("1", "a", active_multipliers=[Properties.Multiplier(0.2)]),
            Streamer("2", "b", active_multipliers=[Properties.Multiplier(0.4)]),
        ],
        1,
        ["b"],
    ],
    [
        [
            Streamer("1", "a", active_multipliers=[Properties.Multiplier(0.4)]),
            Streamer("2", "b", active_multipliers=[Properties.Multiplier(0.2)]),
        ],
        2,
        ["a", "b"],
    ],
    [
        [
            Streamer("1", "a", active_multipliers=[Properties.Multiplier(0.2)]),
            Streamer("2", "b", active_multipliers=[Properties.Multiplier(0.4)]),
        ],
        2,
        ["b", "a"],
    ],
]


@pytest.mark.parametrize("streamers,max_amount,expected_ids", priority_subscribed_data)
def test_priority_subscribed(
    streamers: list[Streamer], max_amount: int, expected_ids: list[str]
):
    streamer_ids = priority_subscribed(streamers, max_amount)
    assert streamer_ids == expected_ids


def priority_selects_none(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    return []


def priority_selects_first(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    return [streamers[0].channel_id]


class TestPrioritySelector:
    basic_priorities = [Priority.STREAK, Priority.SUBSCRIBED, Priority.ORDER]

    priority_function_overrides_all_selects_none = {
        Priority.ORDER: priority_selects_none,
        Priority.POINTS_ASCENDING: priority_selects_none,
        Priority.POINTS_DESCENDING: priority_selects_none,
        Priority.STREAK: priority_selects_none,
        Priority.DROPS: priority_selects_none,
        Priority.SUBSCRIBED: priority_selects_none,
    }

    priority_function_overrides_all_selects_first = {
        Priority.ORDER: priority_selects_first,
        Priority.POINTS_ASCENDING: priority_selects_first,
        Priority.POINTS_DESCENDING: priority_selects_first,
        Priority.STREAK: priority_selects_first,
        Priority.DROPS: priority_selects_first,
        Priority.SUBSCRIBED: priority_selects_first,
    }

    priority_selector_all_selects_none_data = [
        [[], 0, [], []],
        [[], 1, [], []],
        [[], 2, [], []],
        [[], 2, basic_priorities, []],
        [[Streamer("1", "a")], 0, [], []],
        [[Streamer("1", "a")], 1, [], []],
        [[Streamer("1", "a")], 0, basic_priorities, []],
        [[Streamer("1", "a")], 1, basic_priorities, []],
        [[Streamer("1", "a"), Streamer("2", "b")], 2, basic_priorities, []],
    ]

    priority_selector_all_selects_first_data = [
        [[], 0, [], []],
        [[], 1, [], []],
        [[], 2, [], []],
        [[], 2, basic_priorities, []],
        [[Streamer("1", "a")], 0, [], []],
        [[Streamer("1", "a")], 1, [], []],
        [[Streamer("1", "a")], 0, basic_priorities, []],
        [[Streamer("1", "a")], 1, basic_priorities, ["a"]],
        [[Streamer("1", "a"), Streamer("2", "b")], 2, basic_priorities, ["a", "b"]],
    ]

    @pytest.mark.parametrize(
        "streamers,max_amount,priorities,expected_ids",
        priority_selector_all_selects_none_data,
    )
    def test_priority_selector_all_selects_none(
        self,
        streamers: list[Streamer],
        max_amount: int,
        priorities: list[Priority],
        expected_ids: list[str],
    ):
        streamer_ids = PrioritySelector(
            priorities, self.priority_function_overrides_all_selects_none
        ).select(streamers, max_amount)
        assert streamer_ids == expected_ids

    @pytest.mark.parametrize(
        "streamers,max_amount,priorities,expected_ids",
        priority_selector_all_selects_first_data,
    )
    def test_priority_selector_all_selects_first(
        self,
        streamers: list[Streamer],
        max_amount: int,
        priorities: list[Priority],
        expected_ids: list[str],
    ):
        streamer_ids = PrioritySelector(
            priorities, self.priority_function_overrides_all_selects_first
        ).select(streamers, max_amount)
        # Normalise to handle set ordering
        assert set(streamer_ids) == set(expected_ids)

    def test_priority_selector_order_unchanged(self):
        streamers = [Streamer("2", "b", settings=settings_watch_streak_true),
                     Streamer("1", "a", settings=settings_watch_streak_true)]
        selector = PrioritySelector(
            [Priority.STREAK, Priority.DROPS, Priority.SUBSCRIBED, Priority.ORDER],
        )
        selector.select(streamers, 2)
        assert [streamer.username for streamer in streamers] == ["2", "1"]


class TestPriorityGroupSelector:
    streamer_a = Streamer("1", "a", source=StreamerSource.Streamers)
    streamer_b = Streamer("2", "b", source=StreamerSource.Followers)
    streamer_c = Streamer("3", "c", source=StreamerSource.Streamers)

    select_from_all_data = [
        [[], 0, [], [], []],
        [[], 1, [], [], []],
        [[], 2, [], [], []],
        [
            [streamer_a],
            0,
            [],
            [streamer_a],
            [],
        ],
        [
            [streamer_a],
            1,
            [],
            [streamer_a],
            ["a"],
        ],
        [
            [streamer_a],
            1,
            [],
            [streamer_a],
            [],
        ],
        [
            [streamer_a, streamer_b],
            2,
            [],
            [streamer_a, streamer_b],
            ["a", "b"],
        ],
        # Filtered
        [
            [streamer_a, streamer_b],
            2,
            ["1"],
            [streamer_a],
            ["a"],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            ["1", "2", "3"],
            [streamer_a, streamer_b, streamer_c],
            ["a", "b"],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            ["3"],
            [streamer_c],
            ["c"],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            ["2", "3"],
            [streamer_b, streamer_c],
            ["b", "c"],
        ],
        # StreamerSource.Streamers
        [
            [streamer_a, streamer_b, streamer_c],
            0,
            StreamerSource.Streamers,
            [streamer_a, streamer_c],
            []
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            1,
            StreamerSource.Streamers,
            [streamer_a, streamer_c],
            ["a"]
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            StreamerSource.Streamers,
            [streamer_a, streamer_c],
            ["a", "c"]
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            3,
            StreamerSource.Streamers,
            [streamer_a, streamer_c],
            ["a", "c"]
        ],
        # StreamerSource.Followers
        [
            [streamer_a, streamer_b, streamer_c],
            0,
            StreamerSource.Followers,
            [streamer_b],
            []
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            1,
            StreamerSource.Followers,
            [streamer_b],
            ["b"]
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            StreamerSource.Followers,
            [streamer_b],
            ["b"]
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            3,
            StreamerSource.Followers,
            [streamer_b],
            ["b"]
        ],
        # Arbitrary Callable Filter
        [
            [streamer_a, streamer_b, streamer_c],
            0,
            lambda s: s.channel_id in [],
            [],
            []
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            1,
            lambda s: s.channel_id in [],
            [],
            []
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            1,
            lambda s: s.channel_id in ["d"],
            [],
            []
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            lambda s: s.channel_id in ["a", "b", "c"],
            [streamer_a, streamer_b, streamer_c],
            ["a", "b"],
        ],        [
            [streamer_a, streamer_b, streamer_c],
            2,
            lambda s: s.channel_id in ["b", "c"],
            [streamer_b, streamer_c],
            ["b", "c"],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            3,
            lambda s: s.channel_id in ["a", "c"],
            [streamer_a, streamer_c],
            ["a", "c"],
        ],
    ]

    @pytest.mark.parametrize(
        "streamers,max_amount,streamer_filter,expected_filtered_ids,expected_ids",
        select_from_all_data,
    )
    def test_select(
        self,
        streamers: list[Streamer],
        max_amount: int,
        streamer_filter: list[str] | StreamerSource | Callable[[Streamer], bool] | None,
        expected_filtered_ids: list[str],
        expected_ids: list[str],
    ):
        # Mocks

        selector = MagicMock()
        selector.select.return_value = expected_ids

        # Test

        streamer_ids = PriorityGroupSelector(streamer_filter, selector).select(
            streamers, max_amount
        )

        # Assertions

        # Normalise to handle set ordering
        assert set(streamer_ids) == set(expected_ids)

        selector.select.assert_called_once_with(expected_filtered_ids, max_amount)


class SelectAmount(StreamerSelector):
    def __init__(self, amount: int):
        self.amount = amount

    def select(self, streamers: Sequence[Streamer], max_amount: int) -> list[str]:
        return [
            streamer.channel_id
            for streamer in streamers[: min(self.amount, max_amount)]
        ]


class TestNestedSelector:

    select_none_data = [
        [[], 0],
        [[], 1],
        [[], 2],
        [[Streamer("1", "a")], 0],
        [[Streamer("1", "a")], 1],
        [[Streamer("1", "a")], 2],
        [[Streamer("1", "a"), Streamer("2", "b")], 0],
        [[Streamer("1", "a"), Streamer("2", "b")], 1],
        [[Streamer("1", "a"), Streamer("2", "b")], 2],
    ]

    @pytest.mark.parametrize("streamers,max_amount", select_none_data)
    def test_select_none(self, streamers: list[Streamer], max_amount: int):
        selectors = []
        streamer_ids = NestedSelector(selectors).select(streamers, max_amount)

        # Normalise to handle set ordering
        assert set(streamer_ids) == set()

    select_first_data = [
        [[], 0, []],
        [[], 1, []],
        [[], 2, []],
        [[Streamer("1", "a")], 0, []],
        [[Streamer("1", "a")], 1, ["a"]],
        [[Streamer("1", "a")], 2, ["a"]],
        [[Streamer("1", "a"), Streamer("2", "b")], 0, []],
        [[Streamer("1", "a"), Streamer("2", "b")], 1, ["a"]],
        [[Streamer("1", "a"), Streamer("2", "b")], 2, ["a"]],
    ]

    @pytest.mark.parametrize("streamers,max_amount,expected_ids", select_first_data)
    def test_select_first(
        self, streamers: list[Streamer], max_amount: int, expected_ids: list[str]
    ):
        select_first = SelectAmount(1)
        selectors: list[StreamerSelector] = [select_first]

        streamer_ids = NestedSelector(selectors).select(streamers, max_amount)

        # Normalise to handle set ordering
        assert set(streamer_ids) == set(expected_ids)

    multi_selectors_data = [
        [[], 0, []],
        [[], 1, []],
        [[], 2, []],
        [[Streamer("1", "a")], 0, []],
        [[Streamer("1", "a")], 1, ["a"]],
        [[Streamer("1", "a")], 2, ["a"]],
        [[Streamer("1", "a"), Streamer("2", "b")], 0, []],
        [[Streamer("1", "a"), Streamer("2", "b")], 1, ["a"]],
        [[Streamer("1", "a"), Streamer("2", "b")], 2, ["a", "b"]],
        [[Streamer("1", "a"), Streamer("2", "b")], 3, ["a", "b"]],
        [[Streamer("1", "a"), Streamer("2", "b"), Streamer("3", "c")], 0, []],
        [[Streamer("1", "a"), Streamer("2", "b"), Streamer("3", "c")], 1, ["a"]],
        [[Streamer("1", "a"), Streamer("2", "b"), Streamer("3", "c")], 2, ["a", "b"]],
        [
            [Streamer("1", "a"), Streamer("2", "b"), Streamer("3", "c")],
            3,
            ["a", "b", "c"],
        ],
    ]

    @pytest.mark.parametrize("streamers,max_amount,expected_ids", multi_selectors_data)
    def test_multi_selectors(
        self, streamers: list[Streamer], max_amount: int, expected_ids: list[str]
    ):
        select_first = SelectAmount(1)
        select_2 = SelectAmount(2)
        selectors: list[StreamerSelector] = [select_first, select_2]

        streamer_ids = NestedSelector(selectors).select(streamers, max_amount)

        # Normalise to handle set ordering
        assert set(streamer_ids) == set(expected_ids)


def streamer_with_created_at(username: str, _id: str, timestamp: int):
    streamer = Streamer(username, _id, settings=StreamerSettings(watch_streak=True))
    streamer.stream.created_at = datetime.datetime.fromtimestamp(timestamp)
    return streamer


priority_streak_by_earliest_stream_created_at_data = [
    [[], 0, []],
    [[], 1, []],
    [[], 2, []],
    [[], 0, []],
    [[streamer_with_created_at("1", "a", 0)], 1, ["a"]],
    [[streamer_with_created_at("1", "a", 0)], 2, ["a"]],
    [[streamer_with_created_at("1", "a", 0), Streamer("2", "b")], 0, []],
    [
        [streamer_with_created_at("1", "a", 0), streamer_with_created_at("2", "b", 0)],
        1,
        ["a"],
    ],
    [
        [streamer_with_created_at("1", "a", 1), streamer_with_created_at("2", "b", 0)],
        1,
        ["b"],
    ],
    [
        [streamer_with_created_at("1", "a", 0), streamer_with_created_at("2", "b", 1)],
        1,
        ["a"],
    ],
    [
        [streamer_with_created_at("1", "a", 0), streamer_with_created_at("2", "b", 0)],
        2,
        ["a", "b"],
    ],
    [
        [streamer_with_created_at("1", "a", 1), streamer_with_created_at("2", "b", 0)],
        2,
        ["b", "a"],
    ],
    [
        [streamer_with_created_at("1", "a", 0), streamer_with_created_at("2", "b", 1)],
        2,
        ["a", "b"],
    ],
    [
        [streamer_with_created_at("1", "a", 1), streamer_with_created_at("2", "b", 1)],
        2,
        ["a", "b"],
    ],
    [
        [
            streamer_with_created_at("1", "a", 0),
            streamer_with_created_at("2", "b", 0),
            streamer_with_created_at("3", "c", 0),
        ],
        2,
        ["a", "b"],
    ],
    [
        [
            streamer_with_created_at("1", "a", 0),
            streamer_with_created_at("2", "b", 1),
            streamer_with_created_at("3", "c", 2),
        ],
        2,
        ["a", "b"],
    ],
    [
        [
            streamer_with_created_at("1", "a", 2),
            streamer_with_created_at("2", "b", 1),
            streamer_with_created_at("3", "c", 0),
        ],
        2,
        ["c", "b"],
    ],
    [
        [
            streamer_with_created_at("1", "a", 1),
            streamer_with_created_at("2", "b", 0),
            streamer_with_created_at("3", "c", 2),
        ],
        2,
        ["b", "a"],
    ],
    [
        [
            streamer_with_created_at("1", "a", 1),
            streamer_with_created_at("2", "b", 2),
            streamer_with_created_at("3", "c", 0),
        ],
        2,
        ["c", "a"],
    ],
]


@pytest.mark.parametrize(
    "streamers,max_amount,expected_ids", priority_streak_by_earliest_stream_created_at_data
)
def test_priority_streak_by_earliest_stream_created_at(
    streamers: list[Streamer], max_amount: int, expected_ids: list[str]
):
    streamer_ids = priority_streak_by_earliest_stream_created_at(streamers, max_amount)

    # Normalise to handle set ordering
    assert set(streamer_ids) == set(expected_ids)
