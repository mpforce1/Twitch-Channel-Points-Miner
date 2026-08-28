from typing import Any
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.WatchStreakRecovery import (
    BasicConfiguration,
    BasicWatchStreakRecovery,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    Clips,
    Streamer,
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.entities.Video import Video
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip
from TwitchChannelPointsMiner.classes.gql.data.response.FilterableVideoTower import (
    VideoEdge,
)

Settings.logger = MagicMock()


test_can_watch_data = [
    # Settings disabled
    (Streamer("a", "a", settings=StreamerSettings(watch_streak=False)), False),
    # Channel points disabled
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(watch_streak=True),
            channel_points_enabled=False,
        ),
        False,
    ),
    # Online
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(watch_streak=True),
            channel_points_enabled=True,
            is_online=True,
        ),
        False,
    ),
    # No missed streams
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(watch_streak=True),
            channel_points_enabled=True,
            is_online=False,
            watch_streak_missed_streams=set(),
        ),
        False,
    ),
    # Can watch
    (
        Streamer(
            "a",
            "a",
            settings=StreamerSettings(watch_streak=True),
            channel_points_enabled=True,
            is_online=False,
            watch_streak_missed_streams={"broadcast-a"},
        ),
        True,
    ),
]


@pytest.mark.parametrize("streamer,expected", test_can_watch_data)
def test_can_watch(streamer: Streamer, expected: bool):
    recovery = BasicWatchStreakRecovery(
        twitch=MagicMock(),
        streamers=[],
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )

    assert recovery.can_watch(streamer) == expected


def clip(_id: str):
    return Clip(
        _id=_id,
        broadcast_id=f"broadcast-{_id}",
        slug=f"slug-{_id}",
        url=f"url-{_id}",
        title=f"title-{_id}",
        duration_seconds=1,
    )


clip_a = clip("a")
clip_b = clip("b")
clip_c = clip("c")

test_get_clip_data = [
    # No Clips
    (
        Streamer(
            "a",
            clips=Clips(),
            watch_streak_missed_streams=set(),
        ),
        None,
    ),
    (
        Streamer(
            "a",
            clips=Clips(),
            watch_streak_missed_streams={"broadcast-a"},
        ),
        None,
    ),
    (
        Streamer(
            "a",
            clips=Clips(),
            watch_streak_missed_streams={"broadcast-a", "broadcast-b"},
        ),
        None,
    ),
    # Clips but no matching broadcast
    (
        Streamer(
            "a",
            clips=Clips(last_day=[clip_a]),
            watch_streak_missed_streams=set(),
        ),
        None,
    ),
    (
        Streamer(
            "a",
            clips=Clips(last_day=[clip_a]),
            watch_streak_missed_streams={"broadcast-b"},
        ),
        None,
    ),
    (
        Streamer(
            "a",
            clips=Clips(last_day=[clip_a, clip_b]),
            watch_streak_missed_streams={"broadcast-c"},
        ),
        None,
    ),
    (
        Streamer(
            "a",
            clips=Clips(last_day=[clip_a, clip_b, clip_c]),
            watch_streak_missed_streams={"broadcast-d"},
        ),
        None,
    ),
    (
        Streamer(
            "a",
            clips=Clips(last_day=[clip_a, clip_b], last_week=[clip_c]),
            watch_streak_missed_streams={"broadcast-d"},
        ),
        None,
    ),
    # Matching clips and broadcast
    (
        Streamer(
            "a",
            clips=Clips(last_day=[clip_a]),
            watch_streak_missed_streams={"broadcast-a"},
        ),
        clip_a,
    ),
    (
        Streamer(
            "a",
            clips=Clips(last_day=[clip_a, clip_b]),
            watch_streak_missed_streams={"broadcast-b", "broadcast-c"},
        ),
        clip_b,
    ),
    (
        Streamer(
            "a",
            clips=Clips(last_day=[clip_a, clip_b], last_week=[clip_c]),
            watch_streak_missed_streams={"broadcast-c"},
        ),
        clip_c,
    ),
]


@pytest.mark.parametrize("streamer,expected", test_get_clip_data)
def test_get_clip(streamer: Streamer, expected):
    recovery = BasicWatchStreakRecovery(
        twitch=MagicMock(),
        streamers=[],
        config=BasicConfiguration(
            max_clip_watch_seconds=1,
            max_vod_watch_seconds=1,
        ),
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )

    assert recovery.get_clip(streamer) == expected


def vod(_id: str):
    return Video(
        edge=VideoEdge(_id=_id, broadcast_id=f"broadcast-{_id}", length_seconds=1)
    )


vod_a = vod("a")
vod_b = vod("b")
vod_c = vod("c")
vod_d = vod("d")

test_get_vod_data = [
    # No vods
    (Streamer("a", vods=[], watch_streak_missed_streams=set()), None),
    (Streamer("a", vods=[], watch_streak_missed_streams={"broadcast-a"}), None),
    (Streamer("a", vods=[], watch_streak_missed_streams={"broadcast-b"}), None),
    (
        Streamer(
            "a", vods=[], watch_streak_missed_streams={"broadcast-a", "broadcast-b"}
        ),
        None,
    ),
    # Vods but no matching broadcast
    (Streamer("a", vods=[vod_a], watch_streak_missed_streams=set()), None),
    (Streamer("a", vods=[vod_a], watch_streak_missed_streams={"broadcast-b"}), None),
    (Streamer("a", vods=[vod_b], watch_streak_missed_streams={"broadcast-a"}), None),
    (
        Streamer("a", vods=[vod_a, vod_b], watch_streak_missed_streams={"broadcast-c"}),
        None,
    ),
    # Matching vod and broadcast
    (Streamer("a", vods=[vod_a], watch_streak_missed_streams={"broadcast-a"}), vod_a),
    (
        Streamer(
            "a",
            vods=[vod_a, vod_b, vod_c, vod_d],
            watch_streak_missed_streams={"broadcast-c"},
        ),
        vod_c,
    ),
    (
        Streamer(
            "a",
            vods=[vod_b],
            watch_streak_missed_streams={"broadcast-a", "broadcast-b"},
        ),
        vod_b,
    ),
    (
        Streamer(
            "a",
            vods=[vod_a, vod_b, vod_c, vod_d],
            watch_streak_missed_streams={
                "broadcast-a",
                "broadcast-b",
                "broadcast-c",
                "broadcast-d",
            },
        ),
        vod_a,
    ),
]


@pytest.mark.parametrize("streamer,expected", test_get_vod_data)
def test_get_vod(streamer: Streamer, expected):
    recovery = BasicWatchStreakRecovery(
        twitch=MagicMock(),
        streamers=[],
        config=BasicConfiguration(
            max_clip_watch_seconds=1,
            max_vod_watch_seconds=1,
        ),
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )

    assert recovery.get_vod(streamer) == expected


class MockTwitch:
    def __init__(self, _max: int):
        self.count = 0
        self.max = _max

    @property
    def running(self):
        self.count += 1
        return self.count < self.max


def test_run():
    twitch: Any = MockTwitch(4)
    recovery = BasicWatchStreakRecovery(
        twitch=twitch,
        streamers=[],
        config=BasicConfiguration(
            max_clip_watch_seconds=1, max_vod_watch_seconds=1, interval_seconds=0
        ),
        runner=MagicMock(),
        event_manager=MagicMock(spec=EventManager),
    )
    recovery._run = MagicMock()

    recovery.run()

    assert recovery._run.call_count == 2
