import datetime
from math import exp
import time
from typing import Iterable, Sequence, Callable
from unittest.mock import MagicMock, patch

import pytest
from validators import isin

from TwitchChannelPointsMiner.classes.Settings import Priority, StreamerSource
from TwitchChannelPointsMiner.classes.StreamerSelector import (
    FilterSortSelector,
    PriorityGroupSelector,
    PrioritySelector,
    drops,
    group,
    has_drops,
    in_watch_session,
    is_subscribed,
    match_order,
    match_points,
    needs_watch_streak,
    needs_weekly_reward,
    order,
    points_ascending,
    points_descending,
    priority_drops,
    priority_order,
    priority_points_ascending,
    priority_points_descending,
    priority_streak,
    priority_subscribed,
    NestedSelector,
    StreamerSelector,
    priority_streak_by_earliest_stream_created_at,
    priority_subscribed_by_highest_multiplier_then_least_points,
    sort_oldest_stream,
    subscribed,
    under_points_limit,
    sort_points_ascending,
    sort_points_descending,
    watch_session,
    watch_streak,
    weekly_rewards,
)
from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.Stream import Stream
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    Streamer,
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.gql import Properties
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropCampaignDetails,
    TimeBasedDropDetails,
)
from TwitchChannelPointsMiner.classes.gql.data.response.WeeklyRewards import (
    EventConfig,
    WeeklyRewards,
)


def init_settings(streamers: Iterable[Streamer]):
    # Initialise settings points_limit where it hasn't been set
    for streamer in streamers:
        if streamer.settings is None:
            streamer.settings = StreamerSettings(points_limit=False)


test_under_points_limit_data = [
    (
        Streamer(
            "1", "a", channel_points=0, settings=StreamerSettings(points_limit=False)
        ),
        True,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=1_000_000,
            settings=StreamerSettings(points_limit=False),
        ),
        True,
    ),
    (
        Streamer("1", "a", channel_points=0, settings=StreamerSettings(points_limit=0)),
        True,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=1,
            settings=StreamerSettings(points_limit=0),
        ),
        False,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=100,
            settings=StreamerSettings(points_limit=0),
        ),
        False,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=1000,
            settings=StreamerSettings(points_limit=500),
        ),
        False,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=100,
            settings=StreamerSettings(points_limit=1000),
        ),
        True,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=999,
            settings=StreamerSettings(points_limit=1000),
        ),
        True,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=1000,
            settings=StreamerSettings(points_limit=1000),
        ),
        True,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=1001,
            settings=StreamerSettings(points_limit=1000),
        ),
        False,
    ),
    (
        Streamer(
            "1",
            "a",
            channel_points=10000,
            settings=StreamerSettings(points_limit=1000),
        ),
        False,
    ),
]


@pytest.mark.parametrize("streamer,expected", test_under_points_limit_data)
def test_under_points_limit(streamer: Streamer, expected: bool):
    assert under_points_limit(streamer) == expected


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
    init_settings(streamers)
    expected_calls = min(max_amount, len(streamers))
    with patch(
        "TwitchChannelPointsMiner.classes.StreamerSelector.under_points_limit"
    ) as under_points_limit_mock:
        streamer_ids = priority_order(streamers, max_amount)
        assert (
            under_points_limit_mock.call_count == expected_calls
        ), f"under_points_limit should be called {expected_calls} time(s) (min({max_amount}, {len(streamers)}))"
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
    init_settings(streamers)
    expected_calls = len(streamers)
    with patch(
        "TwitchChannelPointsMiner.classes.StreamerSelector.under_points_limit"
    ) as under_points_limit_mock:
        streamer_ids = priority_points_ascending(streamers, max_amount)
        assert (
            under_points_limit_mock.call_count == expected_calls
        ), f"under_points_limit should be called {expected_calls} time(s)"
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
    init_settings(streamers)
    expected_calls = len(streamers)
    with patch(
        "TwitchChannelPointsMiner.classes.StreamerSelector.under_points_limit"
    ) as under_points_limit_mock:
        streamer_ids = priority_points_descending(streamers, max_amount)
        assert (
            under_points_limit_mock.call_count == expected_calls
        ), f"under_points_limit should be called {expected_calls} time(s)"
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
    init_settings(streamers)
    expected_calls = len(streamers)
    with patch(
        "TwitchChannelPointsMiner.classes.StreamerSelector.under_points_limit"
    ) as under_points_limit_mock:
        streamer_ids = priority_subscribed(streamers, max_amount)
        assert (
            under_points_limit_mock.call_count == expected_calls
        ), f"under_points_limit should be called {expected_calls} time(s)"
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
        streamers = [
            Streamer("2", "b", settings=settings_watch_streak_true),
            Streamer("1", "a", settings=settings_watch_streak_true),
        ]
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
            [],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            1,
            StreamerSource.Streamers,
            [streamer_a, streamer_c],
            ["a"],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            StreamerSource.Streamers,
            [streamer_a, streamer_c],
            ["a", "c"],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            3,
            StreamerSource.Streamers,
            [streamer_a, streamer_c],
            ["a", "c"],
        ],
        # StreamerSource.Followers
        [
            [streamer_a, streamer_b, streamer_c],
            0,
            StreamerSource.Followers,
            [streamer_b],
            [],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            1,
            StreamerSource.Followers,
            [streamer_b],
            ["b"],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            StreamerSource.Followers,
            [streamer_b],
            ["b"],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            3,
            StreamerSource.Followers,
            [streamer_b],
            ["b"],
        ],
        # Arbitrary Callable Filter
        [[streamer_a, streamer_b, streamer_c], 0, lambda s: s.channel_id in [], [], []],
        [[streamer_a, streamer_b, streamer_c], 1, lambda s: s.channel_id in [], [], []],
        [
            [streamer_a, streamer_b, streamer_c],
            1,
            lambda s: s.channel_id in ["d"],
            [],
            [],
        ],
        [
            [streamer_a, streamer_b, streamer_c],
            2,
            lambda s: s.channel_id in ["a", "b", "c"],
            [streamer_a, streamer_b, streamer_c],
            ["a", "b"],
        ],
        [
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
    "streamers,max_amount,expected_ids",
    priority_streak_by_earliest_stream_created_at_data,
)
def test_priority_streak_by_earliest_stream_created_at(
    streamers: list[Streamer], max_amount: int, expected_ids: list[str]
):
    streamer_ids = priority_streak_by_earliest_stream_created_at(streamers, max_amount)

    # Normalise to handle set ordering
    assert set(streamer_ids) == set(expected_ids)


# 0 points with multipliers
streamer_a = Streamer(
    "a",
    "a",
    active_multipliers=[Properties.Multiplier(0.1)],
    channel_points=0,
    settings=StreamerSettings(points_limit=False),
)
streamer_b = Streamer(
    "b",
    "b",
    active_multipliers=[Properties.Multiplier(0.4)],
    channel_points=0,
    settings=StreamerSettings(points_limit=False),
)
streamer_c = Streamer(
    "c",
    "c",
    active_multipliers=[Properties.Multiplier(1.0)],
    channel_points=0,
    settings=StreamerSettings(points_limit=False),
)
# No multipliers
streamer_d = Streamer(
    "d", "d", channel_points=0, settings=StreamerSettings(points_limit=False)
)
streamer_e = Streamer(
    "e", "e", channel_points=100, settings=StreamerSettings(points_limit=False)
)
streamer_f = Streamer(
    "f", "f", channel_points=200, settings=StreamerSettings(points_limit=False)
)
# Multipliers and points
streamer_g = Streamer(
    "g",
    "g",
    active_multipliers=[Properties.Multiplier(0.1)],
    channel_points=0,
    settings=StreamerSettings(points_limit=False),
)
streamer_h = Streamer(
    "h",
    "h",
    active_multipliers=[Properties.Multiplier(0.4)],
    channel_points=100,
    settings=StreamerSettings(points_limit=False),
)
streamer_i = Streamer(
    "i",
    "i",
    active_multipliers=[Properties.Multiplier(1.0)],
    channel_points=200,
    settings=StreamerSettings(points_limit=False),
)

all_streamers = [
    streamer_a,
    streamer_b,
    streamer_c,
    streamer_d,
    streamer_e,
    streamer_f,
    streamer_g,
    streamer_h,
    streamer_i,
]

all_streamers_sorted = ["c", "i", "b", "h", "a", "g"]

test_priority_subscribed_by_highest_multiplier_then_least_points_data = [
    # None
    ([], 0, []),
    ([], 1, []),
    ([], 2, []),
    # max_amount
    (all_streamers, 0, []),
    (all_streamers, 1, all_streamers_sorted[:1]),
    (all_streamers, 2, all_streamers_sorted[:2]),
    (all_streamers, 3, all_streamers_sorted[:3]),
    (all_streamers, 4, all_streamers_sorted[:4]),
    (all_streamers, 5, all_streamers_sorted[:5]),
    (all_streamers, 6, all_streamers_sorted[:6]),
    (all_streamers, 7, all_streamers_sorted[:7]),
    (all_streamers, 8, all_streamers_sorted[:8]),
    (all_streamers, 9, all_streamers_sorted[:9]),
    (all_streamers, 10, all_streamers_sorted),
    # 1
    ([streamer_a], 0, []),
    ([streamer_a], 1, ["a"]),
    ([streamer_a], 2, ["a"]),
    # 2
    ([streamer_a, streamer_b], 0, []),
    ([streamer_a, streamer_b], 2, ["b", "a"]),
    ([streamer_a, streamer_c], 2, ["c", "a"]),
    ([streamer_a, streamer_d], 2, ["a"]),
    ([streamer_a, streamer_e], 2, ["a"]),
    ([streamer_a, streamer_f], 2, ["a"]),
    ([streamer_a, streamer_g], 2, ["a", "g"]),
    ([streamer_a, streamer_h], 2, ["h", "a"]),
    ([streamer_a, streamer_i], 2, ["i", "a"]),
    ([streamer_b, streamer_a], 2, ["b", "a"]),
]


@pytest.mark.parametrize(
    "streamers,max_amount,expected",
    test_priority_subscribed_by_highest_multiplier_then_least_points_data,
)
def test_priority_subscribed_by_highest_multiplier_then_least_points(
    streamers: list[Streamer], max_amount: int, expected
):
    assert (
        priority_subscribed_by_highest_multiplier_then_least_points(
            streamers, max_amount
        )
        == expected
    )


# Convenience functions


def streamer(_id: str, points: int = 0):
    return Streamer(f"streamer-{_id}", _id, channel_points=points)


test_filter_sort_selector_data = [
    # All match, None sorting
    (
        lambda s: True,
        None,
        [],
        1,
        [],
    ),
    (
        lambda s: True,
        None,
        [streamer("a")],
        1,
        ["a"],
    ),
    (
        lambda s: True,
        None,
        [streamer("a"), streamer("b")],
        1,
        ["a"],
    ),
    (
        lambda s: True,
        None,
        [streamer("a"), streamer("b")],
        2,
        ["a", "b"],
    ),
    # All match, custom sorts
    (
        lambda s: True,
        [sort_points_ascending],
        [],
        1,
        [],
    ),
    (
        lambda s: True,
        [sort_points_ascending],
        [streamer("a", 0)],
        1,
        ["a"],
    ),
    (
        lambda s: True,
        [sort_points_ascending],
        [streamer("a", 0), streamer("b", 100)],
        1,
        ["a"],
    ),
    (
        lambda s: True,
        [sort_points_ascending],
        [streamer("a", 0), streamer("b", 100)],
        2,
        ["a", "b"],
    ),
    (
        lambda s: True,
        [sort_points_ascending],
        [streamer("a", 100), streamer("b", 0)],
        2,
        ["b", "a"],
    ),
    (
        lambda s: True,
        [sort_points_ascending],
        [streamer("a", 200), streamer("b", 100), streamer("c", 0)],
        2,
        ["c", "b"],
    ),
    # the default sort is order so, on this tie-break, "b" gets priority over "c"
    (
        lambda s: True,
        [sort_points_ascending],
        [streamer("a", 200), streamer("b", 100), streamer("c", 100), streamer("d", 0)],
        2,
        ["d", "b"],
    ),
    (
        lambda s: True,
        [sort_points_ascending],
        [streamer("a", 200), streamer("b", 100), streamer("c", 100), streamer("d", 0)],
        3,
        ["d", "b", "c"],
    ),
    (
        lambda s: True,
        [sort_points_ascending],
        [
            streamer("a", 200),
            streamer("b", 100),
            streamer("c", 100),
            streamer("d", 0),
            streamer("e", 300),
            streamer("f", 10),
            streamer("g", 200),
        ],
        10,
        ["d", "f", "b", "c", "a", "g", "e"],
    ),
    (
        lambda s: True,
        [sort_points_descending],
        [
            streamer("a", 200),
            streamer("b", 100),
            streamer("c", 100),
            streamer("d", 0),
            streamer("e", 300),
            streamer("f", 10),
            streamer("g", 200),
        ],
        10,
        ["e", "a", "g", "b", "c", "f", "d"],
    ),
    # Custom filter, no sort
    (
        lambda s: s.channel_id in {"a", "b", "c"},
        None,
        [
            streamer("a", 200),
            streamer("b", 100),
            streamer("c", 100),
            streamer("d", 0),
            streamer("e", 300),
            streamer("f", 10),
            streamer("g", 200),
        ],
        5,
        ["a", "b", "c"],
    ),
    (
        lambda s: s.channel_id in {"e", "f", "g"},
        None,
        [
            streamer("a", 200),
            streamer("b", 100),
            streamer("c", 100),
            streamer("d", 0),
            streamer("e", 300),
            streamer("f", 10),
            streamer("g", 200),
        ],
        5,
        ["e", "f", "g"],
    ),
    # Custom filter and sort
    (
        lambda s: s.channel_id in {"e", "f", "g"},
        [sort_points_ascending],
        [
            streamer("a", 200),
            streamer("b", 100),
            streamer("c", 100),
            streamer("d", 0),
            streamer("e", 300),
            streamer("f", 10),
            streamer("g", 200),
        ],
        5,
        ["f", "g", "e"],
    ),
]


@pytest.mark.parametrize(
    "_filter,sorting,streamers,max_amount,expected", test_filter_sort_selector_data
)
def test_filter_sort_selector(_filter, sorting, streamers, max_amount, expected):
    selector = FilterSortSelector(reason="test", _filter=_filter, sorting=sorting)

    assert selector.select(streamers, max_amount) == expected


test_match_order_data = [
    (
        Streamer("a", channel_points=0, settings=StreamerSettings(points_limit=False)),
        True,
    ),
    (
        Streamer(
            "a", channel_points=1000000, settings=StreamerSettings(points_limit=False)
        ),
        True,
    ),
    (
        Streamer("a", channel_points=0, settings=StreamerSettings(points_limit=1000)),
        True,
    ),
    (
        Streamer(
            "a", channel_points=1001, settings=StreamerSettings(points_limit=1000)
        ),
        False,
    ),
]


@pytest.mark.parametrize("streamer,expected", test_match_order_data)
def test_match_order(streamer, expected):
    assert match_order(streamer) == expected


# They have exactly the same requirements
test_match_points_data = test_match_order_data


@pytest.mark.parametrize("streamer,expected", test_match_points_data)
def test_match_points(streamer, expected):
    assert match_points(streamer) == expected


stream_watch_streak_not_missing = Stream()
stream_watch_streak_not_missing.watch_streak_missing = False

stream_watch_streak_missing = Stream()
stream_watch_streak_missing.watch_streak_missing = True

test_needs_watch_streak_data = [
    (Streamer("a", settings=StreamerSettings(watch_streak=False)), False),
    (
        Streamer(
            "a",
            settings=StreamerSettings(watch_streak=True),
            stream=stream_watch_streak_not_missing,
        ),
        False,
    ),
    (
        Streamer(
            "a",
            settings=StreamerSettings(watch_streak=True),
            offline_at=0,
            stream=stream_watch_streak_not_missing,
        ),
        False,
    ),
    (
        Streamer(
            "a",
            settings=StreamerSettings(watch_streak=True),
            offline_at=0,
            stream=stream_watch_streak_missing,
        ),
        True,
    ),
]


@pytest.mark.parametrize("streamer,expected", test_needs_watch_streak_data)
def test_needs_watch_streak(streamer, expected):
    assert needs_watch_streak(streamer) == expected


def test_has_drops():
    streamer_1 = Streamer("a", settings=StreamerSettings(claim_drops=False))
    assert has_drops(streamer_1) is False
    drop = TimeBasedDropDetails(
        _id="",
        name="",
        end_at=datetime.datetime.now(),
        start_at=datetime.datetime.now(),
        benefits=[],
        required_minutes_watched=10,
        required_subs=0,
    )
    stream = Stream()
    stream.campaigns = [
        Campaign(
            data=DropCampaignDetails(
                _id="",
                name="",
                status="",
                game=MagicMock(),
                allow_channel_ids=None,
                start_at=datetime.datetime.now(),
                end_at=datetime.datetime.now(),
                time_based_drops=[drop],
            )
        )
    ]
    stream.campaigns[0].drops[0].is_claimable = True
    streamer_2 = Streamer(
        "b", is_online=True, settings=StreamerSettings(claim_drops=True), stream=stream
    )
    assert has_drops(streamer_2) is True


teat_is_subscribed_data = [
    (
        Streamer(
            "a", settings=StreamerSettings(points_limit=False), active_multipliers=[]
        ),
        False,
    ),
    (
        Streamer(
            "a", settings=StreamerSettings(points_limit=1000), active_multipliers=[]
        ),
        False,
    ),
    (
        Streamer(
            "a",
            settings=StreamerSettings(points_limit=1000),
            active_multipliers=[],
            channel_points=1001,
        ),
        False,
    ),
    (
        Streamer(
            "a",
            settings=StreamerSettings(points_limit=1000),
            active_multipliers=[Properties.Multiplier(0.2)],
            channel_points=1001,
        ),
        False,
    ),
    (
        Streamer(
            "a",
            settings=StreamerSettings(points_limit=1000),
            active_multipliers=[Properties.Multiplier(0.2)],
            channel_points=10,
        ),
        True,
    ),
    (
        Streamer(
            "a",
            settings=StreamerSettings(points_limit=False),
            active_multipliers=[Properties.Multiplier(0.2)],
            channel_points=10,
        ),
        True,
    ),
]


@pytest.mark.parametrize("streamer,expected", teat_is_subscribed_data)
def teat_is_subscribed(streamer, expected):
    assert is_subscribed(streamer) == expected


test_in_watch_session_data = [
    (None, False),
    (datetime.datetime.fromisoformat("2026-07-14T20:00:00"), True),
    (datetime.datetime.fromisoformat("2026-07-14T19:59:00"), True),
    (datetime.datetime.fromisoformat("2026-07-14T19:58:00"), True),
    (datetime.datetime.fromisoformat("2026-07-14T19:53:00"), True),
    (datetime.datetime.fromisoformat("2026-07-14T19:52:59"), False),
    (datetime.datetime.fromisoformat("2026-07-14T19:30:00"), False),
]


@pytest.mark.parametrize("watch_session_state,expected", test_in_watch_session_data)
def test_in_watch_session(watch_session_state, expected):
    now_time = datetime.datetime.fromisoformat("2026-07-14T20:00:00")
    streamer = Streamer("a")
    streamer.stream = Stream()
    streamer.stream.watch_session_state = watch_session_state
    with pytest.MonkeyPatch.context() as patcher:

        class MockDateTime:
            @classmethod
            def now(cls, tz=None):
                return now_time

        patcher.setattr(datetime, "datetime", MockDateTime)
        assert in_watch_session(streamer) == expected


test_needs_weekly_reward_data = [
    (Streamer("a", settings=StreamerSettings(weekly_rewards=False)), False, False),
    (
        Streamer(
            "a", settings=StreamerSettings(weekly_rewards=True), weekly_rewards=None
        ),
        True,
        False,
    ),
    (
        Streamer(
            "a",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=0,
                accumulated_weeks=0,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=MagicMock(),
                event_config=EventConfig(
                    _id="",
                    days_required_per_week=3,
                    end_date=MagicMock(),
                    week_reset_dates=[],
                    reward_tiers=[
                        MagicMock(),
                        MagicMock(),
                        MagicMock(),
                        MagicMock(),
                    ],
                ),
            ),
        ),
        True,
        True,
    ),
]


@pytest.mark.parametrize(
    "streamer,watch_streak_missing,expected", test_needs_weekly_reward_data
)
def test_needs_weekly_reward(streamer, watch_streak_missing, expected):
    stream = Stream()
    stream.watch_streak_missing = watch_streak_missing
    streamer.stream = stream
    assert needs_weekly_reward(streamer) == expected


def test_sort_points_ascending():
    assert sort_points_ascending(Streamer("a", channel_points=0)) == 0
    assert sort_points_ascending(Streamer("a", channel_points=100)) == 100
    assert sort_points_ascending(Streamer("a", channel_points=200)) == 200
    assert sort_points_ascending(Streamer("a", channel_points=300)) == 300


def test_sort_points_descending():
    assert sort_points_descending(Streamer("a", channel_points=0)) == 0
    assert sort_points_descending(Streamer("a", channel_points=100)) == -100
    assert sort_points_descending(Streamer("a", channel_points=200)) == -200
    assert sort_points_descending(Streamer("a", channel_points=300)) == -300


def test_sort_oldest_stream():
    assert sort_oldest_stream(Streamer("a", stream=None)) == 0

    stream = Stream()
    stream.created_at = None
    assert sort_oldest_stream(Streamer("a", stream=stream)) == 0

    stream = Stream()
    time.time()
    stream.created_at = datetime.datetime.fromtimestamp(1784121062)
    assert sort_oldest_stream(Streamer("a", stream=stream)) == 1784121062


def test_order():
    sorting = [sort_points_ascending]
    selector = order(sorting=sorting)
    assert isinstance(selector, FilterSortSelector)
    assert selector.filter == match_order
    assert selector.sorting == sorting


def test_watch_streak():
    sorting = [sort_points_ascending]
    selector = watch_streak(sorting=sorting)
    assert isinstance(selector, FilterSortSelector)
    assert selector.filter == needs_watch_streak
    assert selector.sorting == sorting


def test_drops():
    sorting = [sort_points_ascending]
    selector = drops(sorting=sorting)
    assert isinstance(selector, FilterSortSelector)
    assert selector.filter == has_drops
    assert selector.sorting == sorting


def test_subscribed():
    sorting = [sort_points_ascending]
    selector = subscribed(sorting=sorting)
    assert isinstance(selector, FilterSortSelector)
    assert selector.filter == is_subscribed
    assert selector.sorting == sorting


def test_points_ascending():
    sorting = [sort_points_ascending]
    selector = points_ascending(sorting=sorting)
    assert isinstance(selector, FilterSortSelector)
    assert selector.filter == match_points
    assert selector.sorting[0] == sort_points_ascending
    for index in range(len(sorting)):
        assert selector.sorting[index + 1] == sorting[0]


def test_points_descending():
    sorting = [sort_points_descending]
    selector = points_descending(sorting=sorting)
    assert isinstance(selector, FilterSortSelector)
    assert selector.filter == match_points
    assert selector.sorting[0] == sort_points_descending
    for index in range(len(sorting)):
        assert selector.sorting[index + 1] == sorting[0]


def test_watch_session():
    sorting = [sort_points_ascending]
    selector = watch_session(sorting=sorting)
    assert isinstance(selector, FilterSortSelector)
    assert selector.filter == in_watch_session
    assert selector.sorting == sorting


def test_weekly_rewards():
    sorting = [sort_points_ascending]
    selector = weekly_rewards(sorting=sorting)
    assert isinstance(selector, FilterSortSelector)
    assert selector.filter == needs_weekly_reward
    assert selector.sorting == sorting


def test_group():
    streamers = ["a"]
    selector = watch_session()
    group_selector = group(streamers=streamers, selector=selector)
    assert isinstance(group_selector, PriorityGroupSelector)
    assert group_selector.selector == selector
    assert group_selector.streamers == streamers
