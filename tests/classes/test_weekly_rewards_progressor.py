import datetime
import time
from typing import Any
from unittest.mock import MagicMock

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
from TwitchChannelPointsMiner.classes.entities.Video import Video
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
        clips=[],
        vods=[],
    )


def streamer_watchable(username: str, channel_id: str):
    return Streamer(
        username,
        channel_id=channel_id,
        settings=StreamerSettings(weekly_rewards=True),
        weekly_rewards=weekly_rewards_unvisited,
        clips=[
            Clip(
                _id="a",
                slug="example-clip-slug",
                url="clip url",
                title="clip title",
                duration_seconds=10,
            )
        ],
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


test_select_streamers_data = [
    # Test no streamers selects nothing
    ([], 1, set(), []),
    ([], 2, set(), []),
    # Test all unwatchable selects nothing
    ([streamer_unwatchable("streamer1", "123456789")], 1, set(), []),
    ([streamer_unwatchable("streamer1", "123456789")], 2, set(), []),
    # Test watchable gets selected up to limit
    (
        [streamer_watchable("streamer1", "123456789")],
        1,
        set(),
        ["123456789"],
    ),
    (
        [streamer_watchable("streamer1", "123456789")],
        2,
        set(),
        ["123456789"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
        ],
        1,
        set(),
        ["123456789"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
        ],
        2,
        set(),
        ["123456789", "987654321"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
            streamer_watchable("streamer3", channel_id="963258741"),
        ],
        2,
        set(),
        ["123456789", "987654321"],
    ),
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
            streamer_watchable("streamer3", channel_id="963258741"),
        ],
        3,
        set(),
        ["123456789", "987654321", "963258741"],
    ),
    # Test mix of watchable and unwatchable
    (
        [
            streamer_watchable("streamer1", channel_id="123456789"),
            streamer_unwatchable("streamer2", channel_id="987654321"),
        ],
        2,
        set(),
        ["123456789"],
    ),
    (
        [
            streamer_unwatchable("streamer1", channel_id="123456789"),
            streamer_watchable("streamer2", channel_id="987654321"),
        ],
        2,
        set(),
        ["987654321"],
    ),
    # Tests streamers without clips and/or vods
    (
        [
            # Streamer with no clips but 1 vod of the right length
            Streamer(
                "a",
                channel_id="1",
                settings=StreamerSettings(weekly_rewards=True),
                weekly_rewards=weekly_rewards_unvisited,
                clips=[],
                vods=[
                    Video(
                        edge=VideoEdge(
                            _id="a", broadcast_id="a", length_seconds=10 * 60
                        )
                    )
                ],
            ),
            # Streamer with no clips and 1 vod of the wrong length
            Streamer(
                "b",
                channel_id="2",
                settings=StreamerSettings(weekly_rewards=True),
                weekly_rewards=weekly_rewards_unvisited,
                clips=[],
                vods=[
                    Video(edge=VideoEdge(_id="b", broadcast_id="b", length_seconds=10))
                ],
            ),
        ],
        2,
        set(),
        ["1"],
    ),
    (
        [
            # Streamer with 1 clip but no vods
            Streamer(
                "a",
                channel_id="1",
                settings=StreamerSettings(weekly_rewards=True),
                weekly_rewards=weekly_rewards_unvisited,
                clips=[
                    Clip(
                        _id="a",
                        slug="slug",
                        url="url",
                        title="title",
                        duration_seconds=10,
                    )
                ],
                vods=[],
            ),
            # Streamer with 1 clip that's too short and no vods
            Streamer(
                "b",
                channel_id="2",
                settings=StreamerSettings(weekly_rewards=True),
                weekly_rewards=weekly_rewards_unvisited,
                clips=[
                    Clip(
                        _id="b",
                        slug="slug",
                        url="url",
                        title="title",
                        duration_seconds=4,
                    )
                ],
                vods=[],
            ),
        ],
        2,
        set(),
        ["1"],
    ),
    # Test currently watching
    (
        [
            streamer_watchable("a", "a"),
            streamer_watchable("b", "b"),
            streamer_watchable("c", "c"),
            streamer_watchable("d", "d"),
            streamer_watchable("e", "e"),
        ],
        4,
        {"a"},
        ["b", "c", "d"],
    ),
    (
        [
            streamer_watchable("a", "a"),
            streamer_watchable("b", "b"),
            streamer_watchable("c", "c"),
            streamer_watchable("d", "d"),
            streamer_watchable("e", "e"),
        ],
        4,
        {"a", "d"},
        ["b", "c"],
    ),
    (
        [
            streamer_watchable("a", "a"),
            streamer_watchable("b", "b"),
            streamer_watchable("c", "c"),
            streamer_watchable("d", "d"),
            streamer_watchable("e", "e"),
        ],
        5,
        {"a", "d"},
        ["b", "c", "e"],
    ),
    (
        [
            streamer_watchable("a", "a"),
            streamer_watchable("b", "b"),
            streamer_watchable("c", "c"),
            streamer_watchable("d", "d"),
            streamer_watchable("e", "e"),
        ],
        3,
        {"a", "b", "d"},
        [],
    ),
]


@pytest.mark.parametrize(
    "streamers,max_concurrent_watch,currently_watching,expected",
    test_select_streamers_data,
)
def test_select_streamers(
    twitch, streamers, max_concurrent_watch, currently_watching: set[str], expected
):
    max_seconds_clips = 30
    max_minutes_vod = 8

    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=max_concurrent_watch,
        max_seconds_clips=max_seconds_clips,
        max_seconds_vods=max_minutes_vod,
    )

    assert [
        streamer.channel_id
        for streamer in progressor.select_streamers(currently_watching)
    ] == expected


clip_watchable_a = Clip(
    _id="a", slug="slug-a", url="url-a", title="title-a", duration_seconds=10
)
clip_watchable_b = Clip(
    _id="b", slug="slug-b", url="url-b", title="title-b", duration_seconds=20
)
clip_watchable_c = Clip(
    _id="c", slug="slug-c", url="url-c", title="title-c", duration_seconds=6
)

clip_unwatchable_d = Clip(
    _id="d", slug="slug-d", url="url-d", title="title-d", duration_seconds=5
)
clip_unwatchable_e = Clip(
    _id="e", slug="slug-e", url="url-e", title="title-e", duration_seconds=3
)
clip_unwatchable_f = Clip(
    _id="f", slug="slug-f", url="url-f", title="title-f", duration_seconds=1
)

test_get_clips_data = [
    ([], None),
    ([clip_watchable_a], clip_watchable_a),
    ([clip_watchable_a, clip_watchable_b, clip_watchable_c], clip_watchable_a),
    ([clip_unwatchable_d], None),
    ([clip_unwatchable_d, clip_unwatchable_e, clip_unwatchable_f], None),
    ([clip_unwatchable_e, clip_watchable_a], clip_watchable_a),
]


@pytest.mark.parametrize("clips,expected", test_get_clips_data)
def test_get_clip(clips: list[Clip], expected: Clip | None):
    twitch = MagicMock()

    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=[],
        max_concurrent_watch=2,
        max_seconds_clips=30,
        max_seconds_vods=10,
        loop_interval_seconds=20,
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

test_get_vods_data = [
    ([], None),
    ([vod_watchable_a], vod_watchable_a),
    ([vod_watchable_a, vod_watchable_b, vod_watchable_c], vod_watchable_a),
    ([vod_unwatchable_d], None),
    ([vod_unwatchable_d, vod_watchable_b], vod_watchable_b),
    ([vod_unwatchable_d, vod_unwatchable_e, vod_unwatchable_f], None),
    ([vod_unwatchable_e, vod_watchable_a], vod_watchable_a),
]


@pytest.mark.parametrize("vods,expected", test_get_vods_data)
def test_get_vod(vods: list[Video], expected: Video | None):
    twitch = MagicMock()
    twitch.vod_viewable = lambda s, vod: vod.viewable

    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=[],
        max_concurrent_watch=2,
        max_seconds_clips=30,
        max_seconds_vods=10,
        loop_interval_seconds=20,
    )

    streamer = MagicMock()
    streamer.vods = vods

    assert progressor.get_vod(streamer) == (
        expected.edge if expected is not None else None
    )


test_do_watch_data = [
    # All attempts fail
    (
        clip_watchable_a,
        vod_watchable_a,
        False,
        True,
        False,
        True,
        Result(success=False, reason="clip and vod both timed out"),
    ),
    # Clip timeout and no vods
    (
        clip_watchable_a,
        None,
        False,
        True,
        False,
        True,
        Result(
            success=False, reason="clip timed out and streamer has no viewable vods"
        ),
    ),
    # Vod timeout
    (
        None,
        vod_watchable_a,
        False,
        True,
        False,
        True,
        Result(success=False, reason="vod timed out"),
    ),
    # No clips or vods
    (
        None,
        None,
        False,
        True,
        False,
        True,
        Result(success=False, reason="streamer has no clips or vods"),
    ),
    # Fails by miner stopped 2nd time
    (
        None,
        vod_watchable_a,
        False,
        True,
        False,
        False,
        Result(success=False, reason="miner not running"),
    ),
    # Succeeds by VOD
    (
        None,
        vod_watchable_a,
        False,
        True,
        True,
        False,
        Result(success=True, reason="vod"),
    ),
    # Fails by miner stopped 1st time
    (
        clip_watchable_a,
        None,
        False,
        False,
        False,
        False,
        Result(success=False, reason="miner not running"),
    ),
    # Succeeds by clip
    (
        clip_watchable_a,
        None,
        True,
        False,
        False,
        False,
        Result(success=True, reason="clip"),
    ),
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

    def simulate_clip_playback(self, streamer, clip: Clip, max_watch_seconds: float):
        return self.clip

    def simulate_vod_playback(self, streamer, vod: VideoEdge, max_watch_seconds: float):
        return self.vod


@pytest.mark.parametrize(
    "clip,vod,clip_success,running,vod_success,running_2,expected", test_do_watch_data
)
def test_do_watch(
    clip: Clip | None,
    vod: VideoEdge | None,
    clip_success: bool,
    running: bool,
    vod_success: bool,
    running_2: bool,
    expected: Result,
):
    twitch: Any = MockTwitch(clip_success, running, vod_success, running_2)

    streamers = []
    max_concurrent_watch = 2
    max_seconds_clips = 30
    max_seconds_vods = 8

    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=max_concurrent_watch,
        max_seconds_clips=max_seconds_clips,
        max_seconds_vods=max_seconds_vods,
    )

    progressor.get_clip = MagicMock()
    progressor.get_clip.return_value = clip

    progressor.get_vod = MagicMock()
    progressor.get_vod.return_value = vod

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
        max_seconds_vods=8,
    )
    progressor.do_watch = MagicMock()
    progressor.process_result = MagicMock()

    progressor.watch_single(MagicMock())
    progressor.do_watch.assert_called_once()
    progressor.process_result.assert_called_once()


class SlotConfig:
    def __init__(
        self, streamer: Streamer, done, result, start_time, expect_timeout: bool = False
    ) -> None:
        self.streamer = streamer
        self.done = done
        self.result = result
        self.start_time = start_time
        self.expect_timeout = expect_timeout

    def as_magic_mock(self):
        mock = MagicMock()
        mock.future = MagicMock()
        mock.future.done.return_value = self.done
        mock.future.result.return_value = self.result
        mock.start_time = self.start_time
        mock.streamer = self.streamer
        return mock


test_watch_multiple_manages_existing_tasks_data = [
    # Minimum empty slots
    ([None, None], 10, 0, 0),
    # First slot filled but unfinished
    ([SlotConfig(Streamer("a", channel_id="a"), False, None, 0), None], 10, 0, 1),
    # Second slot filled but unfinished
    ([None, SlotConfig(Streamer("a", channel_id="a"), False, None, 0)], 10, 0, 1),
    # First slot finished, second unfinished
    (
        [
            SlotConfig(Streamer("a", channel_id="a"), True, "a done", 0),
            SlotConfig(Streamer("b", channel_id="b"), False, None, 0),
        ],
        10,
        0,
        1,
    ),
    # First slot unfinished, second finished
    (
        [
            SlotConfig(Streamer("a", channel_id="a"), False, None, 0),
            SlotConfig(Streamer("b", channel_id="b"), True, "b done", 0),
        ],
        10,
        0,
        1,
    ),
    # Both done
    (
        [
            SlotConfig(Streamer("a", channel_id="a"), False, "a done", 0),
            SlotConfig(Streamer("b", channel_id="b"), True, None, 0),
        ],
        10,
        0,
        1,
    ),
    # Timeouts
    # Second slot timed out, first unfinished
    (
        [
            SlotConfig(Streamer("a", channel_id="a"), False, None, 10, False),
            SlotConfig(Streamer("b", channel_id="b"), False, None, 9, True),
        ],
        110,
        30,
        1,
    ),
    #
    (
        [
            SlotConfig(Streamer("a", channel_id="a"), False, None, 0, True),
            SlotConfig(Streamer("b", channel_id="b"), False, None, 1, True),
            SlotConfig(Streamer("c", channel_id="c"), False, None, 2, False),
            SlotConfig(Streamer("d", channel_id="d"), False, None, 3, False),
            SlotConfig(Streamer("e", channel_id="e"), False, None, 4, False),
        ],
        17,
        5,
        0,
    ),
]


@pytest.mark.parametrize(
    "slots,current_time,max_seconds_clips,max_minutes_vod",
    test_watch_multiple_manages_existing_tasks_data,
)
def test_manage_slots(
    slots: list[SlotConfig | None],
    current_time,
    max_seconds_clips: int,
    max_minutes_vod: int,
):
    twitch: Any = MockTwitch(clip=False, running=True, vod=False, running_2=False)
    streamers = []
    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=len(slots),
        max_seconds_clips=max_seconds_clips,
        max_seconds_vods=max_minutes_vod,
        loop_interval_seconds=0,
    )
    progressor.select_streamers = MagicMock()
    progressor.select_streamers.return_value = streamers
    progressor.do_watch = MagicMock()
    progressor.watch_single = MagicMock()
    progressor.process_result = MagicMock()

    mock_slots = [slot.as_magic_mock() if slot is not None else None for slot in slots]

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(time, "monotonic", lambda: current_time)
        progressor.manage_slots(mock_slots)

    for slot, mock_slot in zip(slots, mock_slots):
        if slot is not None and mock_slot is not None:
            # We check if it's done once
            mock_slot.future.done.assert_called_once()
            if slot.done:
                # If it's done, we should get the result and process it
                mock_slot.future.result.assert_called_once()
                assert (
                    slot.streamer,
                    slot.result,
                ) in progressor.process_result.call_args_list, (
                    f"Result for {slot.streamer} was not processed"
                )
            elif slot.expect_timeout:
                mock_slot.future.cancel.assert_called_once()


@pytest.mark.parametrize("streamers_amount", [amount for amount in range(10)])
def test_watch_loop_single(streamers_amount: int):
    twitch: Any = MockTwitch(clip=False, running=True, vod=False, running_2=False)
    streamers = [Streamer(f"streamer{index}") for index in range(streamers_amount)]
    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=1,
        max_seconds_clips=30,
        max_seconds_vods=8,
        loop_interval_seconds=0,
    )
    progressor.select_streamers = MagicMock()
    progressor.select_streamers.return_value = streamers
    progressor.watch_single = MagicMock()

    progressor.watch_loop()

    progressor.select_streamers.assert_called_once()
    if streamers_amount > 0:
        progressor.watch_single.assert_called_once()


@pytest.mark.parametrize("max_concurrent_watch", [x for x in range(2, 10)])
def test_watch_loop_multiple(max_concurrent_watch: int):
    twitch: Any = MockTwitch(clip=False, running=True, vod=False, running_2=False)
    streamers = []
    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=max_concurrent_watch,
        max_seconds_clips=1,
        max_seconds_vods=1,
        loop_interval_seconds=0,
    )
    progressor.manage_slots = MagicMock()
    progressor.watch_multiple = MagicMock()

    progressor.watch_loop()

    progressor.manage_slots.assert_called_once()
    progressor.watch_multiple.assert_called_once()


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
            clips=[],
            vods=[],
        ),
        # Not enrolled
        Streamer(
            "b",
            channel_id="b",
            settings=StreamerSettings(weekly_rewards=True),
            weekly_rewards=None,
            clips=[],
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
            clips=[],
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
            clips=[],
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
            clips=[],
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
            clips=[],
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
            clips=[clip_watchable_a],
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
            clips=[],
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
            clips=[clip_watchable_b],
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
            clips=[clip_watchable_c],
            vods=[vod_watchable_c],
        ),
    ]

    progressor = WeeklyRewardsProgressor(
        twitch=twitch,
        streamers=streamers,
        max_concurrent_watch=3,
        max_seconds_clips=4,
        max_seconds_vods=5,
        loop_interval_seconds=1,
    )

    twitch.vod_watchable = lambda _, vod: vod.id in {"a", "b", "c"}

    def mock_clip_playback(streamer: Streamer, clip: Clip, max_watch_seconds: float):
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

    def mock_vod_playback(streamer: Streamer, vod: VideoEdge, max_watch_seconds: float):
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
