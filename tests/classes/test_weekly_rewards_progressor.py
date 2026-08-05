import datetime
import time
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes import Anonymiser
from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunnerThread,
)
from TwitchChannelPointsMiner.classes.WeeklyRewardsProgressor import (
    Result,
    BasicWeeklyRewardsProgressor,
    BasicConfiguration,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    Clips,
    Streamer,
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.entities.Video import Video
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.events.managers.Delegate import DelegatingManager
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip
from TwitchChannelPointsMiner.classes.gql.data.response.FilterableVideoTower import (
    VideoEdge,
)
from TwitchChannelPointsMiner.classes.gql.data.response.PlaybackAccessToken import (
    VideoPlaybackAccessToken,
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
        clips=Clips(),
        vods=[],
    )


def streamer_watchable(username: str, channel_id: str):
    return Streamer(
        username,
        channel_id=channel_id,
        settings=StreamerSettings(weekly_rewards=True),
        weekly_rewards=weekly_rewards_unvisited,
        clips=Clips(
            all_time=[
                Clip(
                    _id="a",
                    broadcast_id="broadcast-a",
                    slug="example-clip-slug",
                    url="clip url",
                    title="clip title",
                    duration_seconds=10,
                )
            ]
        ),
        vods=[
            Video(
                edge=VideoEdge(_id="b", broadcast_id="c", length_seconds=10 * 60),
                token=VideoPlaybackAccessToken(value="token", signature="signature"),
            )
        ],
    )


def streamer_setting_disabled(username: str, channel_id: str):
    return Streamer(
        username,
        channel_id=channel_id,
        settings=StreamerSettings(weekly_rewards=False),
        weekly_rewards=weekly_rewards_unvisited,
    )


test_can_watch_data = [
    # Online
    (Streamer("a", "a", is_online=True), False),
    # Offline, not missing reward
    (
        Streamer(
            "a", "a", is_online=False, settings=StreamerSettings(weekly_rewards=False)
        ),
        False,
    ),
    (
        Streamer(
            "a",
            "a",
            is_online=False,
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=False,
        ),
        False,
    ),
    (
        Streamer(
            "a",
            "a",
            is_online=False,
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=True,
            weekly_rewards=weekly_rewards_visited,
        ),
        False,
    ),
    # Can progress
    (
        Streamer(
            "a",
            "a",
            is_online=False,
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=True,
            weekly_rewards=weekly_rewards_unvisited,
        ),
        True,
    ),
]


@pytest.mark.parametrize(
    "streamer,expected",
    test_can_watch_data,
)
def test_can_watch(streamer: Streamer, expected):
    progressor = BasicWeeklyRewardsProgressor(
        twitch=MagicMock(),
        streamers=[],
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )

    assert progressor.can_watch(streamer) == expected


test_done_watching_data = [
    # Done
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=True,
            weekly_rewards=weekly_rewards_visited,
        ),
        True,
    ),
    # Fully unvisited
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=True,
            weekly_rewards=weekly_rewards_unvisited,
        ),
        False,
    ),
    # Not visited today nor has this week
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=True,
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=1,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[0],
                event_config=event_config,
            ),
        ),
        False,
    ),
    # Not visited today but has this week
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=True,
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=1,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=True,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[0],
                event_config=event_config,
            ),
        ),
        True,
    ),
    # Not visited this day or has this week but has all rewards
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=True,
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=1,
                accumulated_weeks=4,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[3],
                event_config=event_config,
            ),
        ),
        True,
    ),
    # Visited today but doesn't yet have this week
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=True,
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=1,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=True,
                current_reward=event_config.reward_tiers[0],
                event_config=event_config,
            ),
        ),
        True,
    ),
    # Channel points have been disabled mid-event
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(weekly_rewards=True),
            channel_points_enabled=False,
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=1,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[0],
                event_config=event_config,
            ),
        ),
        True,
    ),
]


@pytest.mark.parametrize("streamer,expected", test_done_watching_data)
def test_done_watching(streamer: Streamer, expected):
    progressor = BasicWeeklyRewardsProgressor(
        twitch=MagicMock(),
        streamers=[],
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )

    assert progressor.done_watching(streamer) == expected


clip_watchable_a = Clip(
    _id="a",
    broadcast_id="broadcast-a",
    slug="slug-a",
    url="url-a",
    title="title-a",
    duration_seconds=10,
)
clip_watchable_b = Clip(
    _id="b",
    broadcast_id="broadcast-b",
    slug="slug-b",
    url="url-b",
    title="title-b",
    duration_seconds=20,
)
clip_watchable_c = Clip(
    _id="c",
    broadcast_id="broadcast-c",
    slug="slug-c",
    url="url-c",
    title="title-c",
    duration_seconds=6,
)

clip_unwatchable_d = Clip(
    _id="d",
    broadcast_id="broadcast-d",
    slug="slug-d",
    url="url-d",
    title="title-d",
    duration_seconds=5,
)
clip_unwatchable_e = Clip(
    _id="e",
    broadcast_id="broadcast-e",
    slug="slug-e",
    url="url-e",
    title="title-e",
    duration_seconds=3,
)
clip_unwatchable_f = Clip(
    _id="f",
    broadcast_id="broadcast-f",
    slug="slug-f",
    url="url-f",
    title="title-f",
    duration_seconds=1,
)

test_get_clip_data = [
    (Clips(), None),
    (Clips(all_time=[clip_watchable_a]), clip_watchable_a),
    (
        Clips(all_time=[clip_watchable_a, clip_watchable_b, clip_watchable_c]),
        clip_watchable_a,
    ),
    (Clips(all_time=[clip_unwatchable_d]), None),
    (
        Clips(all_time=[clip_unwatchable_d, clip_unwatchable_e, clip_unwatchable_f]),
        None,
    ),
    (Clips(all_time=[clip_unwatchable_e, clip_watchable_a]), clip_watchable_a),
]


@pytest.mark.parametrize("clips,expected", test_get_clip_data)
def test_get_clip(clips: Clips, expected: Clip | None):
    twitch = MagicMock()

    progressor = BasicWeeklyRewardsProgressor(
        twitch=twitch,
        streamers=[],
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )

    streamer = MagicMock()
    streamer.clips = clips

    assert progressor.get_clip(streamer) == expected


vod_watchable_a = Video(
    edge=VideoEdge(_id="a", broadcast_id="a", length_seconds=10 * 60),
    token=VideoPlaybackAccessToken(value="value", signature="signature"),
    viewable=True,
)

vod_watchable_b = Video(
    edge=VideoEdge(_id="b", broadcast_id="b", length_seconds=20 * 60),
    token=VideoPlaybackAccessToken(value="value", signature="signature"),
    viewable=True,
)

vod_watchable_c = Video(
    edge=VideoEdge(_id="c", broadcast_id="c", length_seconds=6 * 60),
    token=VideoPlaybackAccessToken(value="value", signature="signature"),
    viewable=True,
)

# Got token but unviewable
vod_unwatchable_d = Video(
    edge=VideoEdge(_id="d", broadcast_id="d", length_seconds=6 * 60),
    token=VideoPlaybackAccessToken(value="value", signature="signature"),
    viewable=False,
)

# Too short
vod_unwatchable_e = Video(
    edge=VideoEdge(_id="e", broadcast_id="e", length_seconds=5 * 60),
    token=VideoPlaybackAccessToken(value="value", signature="signature"),
    viewable=True,
)

vod_unwatchable_f = Video(
    edge=VideoEdge(_id="e", broadcast_id="e", length_seconds=1 * 60),
    token=VideoPlaybackAccessToken(value="value", signature="signature"),
    viewable=True,
)

test_get_vod_data = [
    ([], None),
    ([vod_watchable_a], vod_watchable_a),
    ([vod_watchable_a, vod_watchable_b, vod_watchable_c], vod_watchable_a),
    ([vod_unwatchable_d], None),
    ([vod_unwatchable_d, vod_watchable_b], vod_watchable_b),
    ([vod_unwatchable_d, vod_unwatchable_e, vod_unwatchable_f], None),
    ([vod_unwatchable_e, vod_watchable_a], vod_watchable_a),
]


@pytest.mark.parametrize("vods,expected", test_get_vod_data)
def test_get_vod(vods: list[Video], expected: Video | None):
    twitch = MagicMock()
    twitch.vod_viewable = lambda _, vod: vod.viewable

    progressor = BasicWeeklyRewardsProgressor(
        twitch=twitch,
        streamers=[],
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )

    streamer = MagicMock()
    streamer.vods = vods

    assert progressor.get_vod(streamer) == expected


test_update_failures_data = [
    # 0 failures
    ("a", {}, {}, 0, 0, {}, {"a": 0}),
    ("a", {}, {"b": 0}, 0, 0, {}, {"a": 0, "b": 0}),
    # 1 failures
    ("a", {}, {}, 1, 0, {}, {"a": 0}),
    ("a", {}, {"b": 0}, 1, 0, {}, {"a": 0, "b": 0}),
    # 2 failures
    ("a", {}, {}, 2, 0, {"a": 1}, {}),
    ("a", {"a": 1}, {}, 2, 0, {}, {"a": 0}),
    ("a", {}, {"b": 0}, 2, 0, {"a": 1}, {"b": 0}),
    # 3 failures
    ("a", {}, {}, 3, 0, {"a": 1}, {}),
    ("a", {"a": 1}, {}, 3, 0, {"a": 2}, {}),
    ("a", {"a": 2}, {}, 3, 0, {}, {"a": 0}),
]


@pytest.mark.parametrize(
    "streamer_id,failures,cooldowns,max_failures_per_streamer,current_time,expected_failures,expected_cooldowns",
    test_update_failures_data,
)
def test_update_failures(
    twitch,
    streamer_id: str,
    failures: dict[str, int],
    cooldowns: dict[str, float],
    max_failures_per_streamer: int,
    current_time: float,
    expected_failures: dict[str, int],
    expected_cooldowns: dict[str, float],
):
    progressor = BasicWeeklyRewardsProgressor(
        twitch,
        streamers=[],
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
        config=BasicConfiguration(
            max_failures_per_streamer=max_failures_per_streamer,
        ),
    )
    progressor._failures = failures
    progressor._cooldowns = cooldowns

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(time, "monotonic", lambda: current_time)
        progressor.update_failures(streamer_id)

    assert progressor._failures == expected_failures
    assert progressor._cooldowns == expected_cooldowns


test_process_result_data = [
    (Streamer("a", "a"), Result(success=True, reason=""), False, True, True),
    (Streamer("a", "a"), Result(success=False, reason=""), True, False, False),
]


@pytest.mark.parametrize(
    "streamer,result,expect_call_update_failures,expect_pop_failures,expect_pop_cooldowns",
    test_process_result_data,
)
def test_process_result(
    twitch,
    streamer: Streamer,
    result: Result,
    expect_call_update_failures: bool,
    expect_pop_failures: bool,
    expect_pop_cooldowns: bool,
):
    progressor = BasicWeeklyRewardsProgressor(
        twitch,
        streamers=[],
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )
    progressor.update_failures = MagicMock()
    progressor._failures = MagicMock()
    progressor._cooldowns = MagicMock()

    progressor.process_result(streamer, result)

    if expect_call_update_failures:
        progressor.update_failures.assert_called_once_with(streamer.channel_id)
    if expect_pop_failures:
        progressor._failures.pop.assert_called_once_with(streamer.channel_id, None)
    if expect_pop_cooldowns:
        progressor._cooldowns.pop.assert_called_once_with(streamer.channel_id, None)


def test_full():
    twitch = MagicMock()
    twitch.running = True

    def mock_vod_viewable(streamer, video: Video):
        return video.viewable

    twitch.vod_viewable = mock_vod_viewable

    streamers = [
        # Not enrolled
        Streamer(
            "a",
            channel_id="a",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=None,
            clips=Clips(),
            vods=[],
        ),
        # Not enrolled
        Streamer(
            "b",
            channel_id="b",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=None,
            clips=Clips(),
            vods=[],
        ),
        # Enrolled but already completed this week
        Streamer(
            "c",
            channel_id="c",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=3,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=True,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[1],
                event_config=event_config,
            ),
            clips=Clips(),
            vods=[],
        ),
        # Enrolled but has completed today
        Streamer(
            "d",
            channel_id="d",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=2,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=True,
                current_reward=event_config.reward_tiers[1],
                event_config=event_config,
            ),
            clips=Clips(),
            vods=[],
        ),
        # Enrolled and ready, but no clips/vods
        Streamer(
            "e",
            channel_id="e",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=2,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[1],
                event_config=event_config,
            ),
            clips=Clips(),
            vods=[],
        ),
        # Enrolled and ready, but no clips and no watchable vods
        Streamer(
            "f",
            channel_id="f",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=2,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[1],
                event_config=event_config,
            ),
            clips=Clips(),
            vods=[vod_unwatchable_d],
        ),
        # Enrolled and ready, clip works
        Streamer(
            "g",
            channel_id="g",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=2,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[1],
                event_config=event_config,
            ),
            clips=Clips(all_time=[clip_watchable_a]),
            vods=[],
        ),
        # Enrolled and ready, vod times out
        Streamer(
            "h",
            channel_id="h",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=2,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[1],
                event_config=event_config,
            ),
            clips=Clips(all_time=[]),
            vods=[vod_watchable_a],
        ),
        # Enrolled and ready, clip times out, vod works
        Streamer(
            "i",
            channel_id="i",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=2,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[1],
                event_config=event_config,
            ),
            clips=Clips(all_time=[clip_watchable_b]),
            vods=[vod_watchable_b],
        ),
        # Enrolled and ready, both time out
        Streamer(
            "j",
            channel_id="j",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=WeeklyRewards(
                days_visited_this_week=2,
                accumulated_weeks=1,
                has_earned_weekly_reward_this_week=False,
                has_visited_today=False,
                current_reward=event_config.reward_tiers[1],
                event_config=event_config,
            ),
            clips=Clips(all_time=[clip_watchable_c]),
            vods=[vod_watchable_c],
        ),
    ]

    # Use a delegating manager with no delegate
    event_manager = DelegatingManager()

    progressor = BasicWeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        runner=SlottedTaskRunnerThread(
            name="Test",
            max_concurrent=3,
            loop_interval_seconds=1,
            event_manager=event_manager,
        ),
        event_manager=event_manager,
        config=BasicConfiguration(
            max_clip_watch_seconds=4,
            max_vod_watch_seconds=5,
            interval_seconds=1,
        ),
    )

    twitch.vod_watchable = lambda _, vod: vod.id in {"a", "b", "c"}

    def mock_clip_playback(
        streamer: Streamer, clip: Clip, max_watch_seconds: float, done
    ):
        if clip.id == "a":
            time.sleep(0.5)
            streamer.weekly_rewards.has_visited_today = True
            return True
        elif clip.id == "b":
            time.sleep(max_watch_seconds)
            return False
        elif clip.id == "c":
            time.sleep(max_watch_seconds)
            return False
        else:
            raise ValueError(f"Unknown clip {clip.id}")

    def mock_vod_playback(
        streamer: Streamer, vod: VideoEdge, max_watch_seconds: float, done
    ):
        if vod.id == "a":
            time.sleep(max_watch_seconds)
            return False
        elif vod.id == "b":
            time.sleep(0.5)
            streamer.weekly_rewards.has_visited_today = True
            return True
        elif vod.id == "c":
            time.sleep(max_watch_seconds)
            return False
        else:
            raise ValueError(f"Unknown vod {vod.id}")

    twitch.simulate_clip_playback = mock_clip_playback
    twitch.simulate_vod_playback = mock_vod_playback

    def assert_valid_targets(missing_set: set[str]):
        for streamer in streamers:
            valid_target = streamer.missing_weekly_reward() and (
                progressor.get_clip(streamer) is not None
                or progressor.get_vod(streamer) is not None
            )
            in_set = streamer.channel_id in missing_set
            assert (
                valid_target == in_set
            ), f"Streamer {streamer.username}: valid_target={valid_target} but in_set={in_set}"

    # Before starting
    assert_valid_targets({"g", "h", "i", "j"})

    progressor.start()

    # After 0.25s nothing should have yet advanced
    time.sleep(0.25)
    assert_valid_targets({"g", "h", "i", "j"})

    # After 1.25s, clip a should have advanced streamer g
    time.sleep(1)
    assert_valid_targets({"h", "i", "j"})

    # After 10 seconds all streamers should be done except j and h
    time.sleep(8.75)

    twitch.running = False

    time.sleep(2)
    assert_valid_targets({"j", "h"})
