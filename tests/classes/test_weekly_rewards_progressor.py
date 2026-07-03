import datetime
from typing import Any
from unittest.mock import MagicMock, call

import pytest

from TwitchChannelPointsMiner.classes import Anonymiser
from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.WeeklyRewardsProgressor import (
    Result,
    WeeklyRewardsProgressor,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    Streamer,
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.gql.data.response.WeeklyRewards import (
    Badge,
    EventConfig,
    RewardTier,
    WeeklyRewards,
)
from TwitchChannelPointsMiner.logger import LoggerSettings

logger_settings = LoggerSettings(anonymiser=Anonymiser.Deanonymiser())
Settings.logger = logger_settings


@pytest.fixture
def twitch():
    return MagicMock()


badge = Badge(
    _id="a",
    set_id="b",
    version="c",
    title="d",
    image_1x="e",
    image_2x="f",
    image_4x="g",
    click_action="h",
    click_url="i",
)

event_config = EventConfig(
    _id="a",
    days_required_per_week=3,
    end_date=datetime.datetime(2026, 7, 26),
    week_reset_dates=[
        datetime.datetime(2026, 7, 5),
        datetime.datetime(2026, 7, 12),
        datetime.datetime(2026, 7, 19),
        datetime.datetime(2026, 7, 26),
    ],
    reward_tiers=[
        RewardTier(tier=1, channel_points=100, badge=badge),
        RewardTier(tier=2, channel_points=200, badge=badge),
        RewardTier(tier=3, channel_points=300, badge=badge),
        RewardTier(tier=4, channel_points=400, badge=badge),
    ],
)

weekly_rewards_unvisited = WeeklyRewards(
    days_visited_this_week=0,
    accumulated_weeks=0,
    has_earned_weekly_reward_this_week=False,
    has_visited_today=False,
    current_reward=RewardTier(tier=1, channel_points=100, badge=badge),
    event_config=event_config,
)

weekly_rewards_visited = WeeklyRewards(
    days_visited_this_week=3,
    accumulated_weeks=1,
    has_earned_weekly_reward_this_week=True,
    has_visited_today=True,
    current_reward=RewardTier(tier=2, channel_points=200, badge=badge),
    event_config=event_config,
)


def streamer_unwatchable(username: str, channel_id: str):
    return Streamer(
        username,
        channel_id=channel_id,
        settings=StreamerSettings(weekly_rewards=False),
        weekly_rewards=weekly_rewards_visited,
    )


def streamer_watchable(username: str, channel_id: str):
    return Streamer(
        username,
        channel_id=channel_id,
        settings=StreamerSettings(weekly_rewards=True),
        weekly_rewards=weekly_rewards_unvisited,
    )


def streamer_setting_disabled(username: str, channel_id: str):
    return Streamer(
        username,
        channel_id=channel_id,
        settings=StreamerSettings(weekly_rewards=False),
        weekly_rewards=weekly_rewards_unvisited,
    )


test_select_streamers_data = [
    ([], 1, []),
    ([], 2, []),
    ([streamer_unwatchable("streamer1", "123456789")], 1, []),
    ([streamer_unwatchable("streamer1", "123456789")], 2, []),
    (
        [streamer_watchable("streamer1", "123456789")],
        1,
        ["123456789"],
    ),
    (
        [streamer_watchable("streamer1", "123456789")],
        2,
        ["123456789"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
        ],
        1,
        ["123456789"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
        ],
        2,
        ["123456789", "987654321"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_unwatchable("streamer2", channel_id="987654321"),
        ],
        2,
        ["123456789"],
    ),
    (
        [
            streamer_unwatchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
        ],
        2,
        ["987654321"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
            streamer_watchable("streamer3", channel_id="963258741"),
        ],
        2,
        ["123456789", "987654321"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
            streamer_watchable("streamer3", channel_id="963258741"),
        ],
        3,
        ["123456789", "987654321", "963258741"],
    ),
]


@pytest.mark.parametrize(
    "streamers,max_concurrent_watch,expected", test_select_streamers_data
)
def test_select_streamers(twitch, streamers, max_concurrent_watch, expected):
    max_seconds_clips = 30
    max_minutes_vod = 8

    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=max_concurrent_watch,
        max_seconds_clips=max_seconds_clips,
        max_minutes_vod=max_minutes_vod,
    )

    assert [
        streamer.channel_id for streamer in progressor.select_streamers()
    ] == expected


test_do_watch_data = [
    # All attempts fail
    (False, True, False, True, Result(success=False, reason="both failed")),
    # Fails by miner stopped 2nd time
    (False, True, False, False, Result(success=False, reason="miner not running")),
    # Succeeds by VOD
    (False, True, True, False, Result(success=True, reason="vod")),
    # Fails by miner stopped 1st time
    (False, False, False, False, Result(success=False, reason="miner not running")),
    # Succeeds by clip
    (True, False, False, False, Result(success=True, reason="clip")),
]


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

    def simulate_clip_playback(self, streamer, max_wait_seconds: int):
        return self.clip

    def simulate_vod_playback(self, streamer, max_minutes: int):
        return self.vod


@pytest.mark.parametrize("clip,running,vod,running_2,expected", test_do_watch_data)
def test_do_watch(
    clip: bool, running: bool, vod: bool, running_2: bool, expected: Result
):
    twitch: Any = MockTwitch(clip, running, vod, running_2)

    streamers = []
    max_concurrent_watch = 2
    max_seconds_clips = 30
    max_minutes_vod = 8

    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=max_concurrent_watch,
        max_seconds_clips=max_seconds_clips,
        max_minutes_vod=max_minutes_vod,
    )

    streamer = MagicMock()

    assert progressor.do_watch(streamer) == expected


def test_process_result():
    # Process result currently just logs, nothing to test
    pass


def test_watch_single():
    progressor = WeeklyRewardsProgressor(
        twitch=MagicMock(),
        streamers=[],
        max_concurrent_watch=2,
        max_seconds_clips=30,
        max_minutes_vod=8,
    )
    progressor.do_watch = MagicMock()
    progressor.process_result = MagicMock()

    progressor.watch_single(MagicMock())
    progressor.do_watch.assert_called_once()
    progressor.process_result.assert_called_once()


test_watch_loop_single_data = [amount for amount in range(10)]


@pytest.mark.parametrize("streamers_amount", test_watch_loop_single_data)
def test_watch_loop_single(streamers_amount: int):
    twitch: Any = MockTwitch(clip=False, running=True, vod=False, running_2=False)
    streamers = [Streamer(f"streamer{index}") for index in range(streamers_amount)]
    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=1,
        max_seconds_clips=30,
        max_minutes_vod=8,
        loop_interval_seconds=0,
    )
    progressor.select_streamers = MagicMock()
    progressor.select_streamers.return_value = streamers
    progressor.watch_single = MagicMock()

    progressor.watch_loop()

    progressor.select_streamers.assert_called_once()
    if streamers_amount > 0:
        progressor.watch_single.assert_called_once()


# Test selecting 0-20 streamers with a range of concurrent watching 2-10
test_watch_loop_multiple_data = [
    (max_concurrent_watch, selected_amount)
    for selected_amount in range(0, 20)
    for max_concurrent_watch in range(2, 10)
]


@pytest.mark.parametrize(
    "max_concurrent_watch,selected_amount", test_watch_loop_multiple_data
)
def test_watch_loop_multiple(max_concurrent_watch: int, selected_amount: int):
    twitch: Any = MockTwitch(clip=False, running=True, vod=False, running_2=False)
    actual_amount = min(max_concurrent_watch, selected_amount)
    streamers = [Streamer(f"streamer{index}") for index in range(actual_amount)]
    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=max_concurrent_watch,
        max_seconds_clips=1,
        max_minutes_vod=1,
        loop_interval_seconds=0,
    )
    progressor.select_streamers = MagicMock()
    progressor.select_streamers.return_value = streamers
    progressor.do_watch = MagicMock()
    progressor.watch_single = MagicMock()
    progressor.process_result = MagicMock()

    progressor.watch_loop()

    progressor.select_streamers.assert_called_once()
    if selected_amount == 1:
        progressor.watch_single.assert_called_once()
    else:
        progressor.do_watch.assert_has_calls(
            [call(streamers[index]) for index in range(actual_amount)], any_order=True
        )
        assert (
            progressor.process_result.call_count == actual_amount
        ), "Not all results were processed"
