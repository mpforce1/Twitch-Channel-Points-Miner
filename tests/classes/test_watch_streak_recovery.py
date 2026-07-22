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
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip
from TwitchChannelPointsMiner.classes.gql.data.response.FilterableVideoTower import (
    VideoEdge,
)

Settings.logger = MagicMock()


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
    )

    assert recovery.get_vod(streamer) == expected


test_recover_clip_data = [
    # No clip
    (Streamer("a"), None, False, False),
    # Clip failed
    (Streamer("a"), clip_a, False, False),
    # Clip success
    (Streamer("a"), clip_a, True, True),
]


test_select_streamers_data = [
    # None
    ([], set(), []),
    ([], {"a", "b"}, []),
    # Single streamer, never selected
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=False),
                clips=Clips(),
                vods=[],
            )
        ],
        set(),
        [],
    ),
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=False,
                clips=Clips(),
                vods=[],
            )
        ],
        set(),
        [],
    ),
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=True,
                clips=Clips(),
                vods=[],
            )
        ],
        set(),
        [],
    ),
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams=set(),
                clips=Clips(),
                vods=[],
            )
        ],
        set(),
        [],
    ),
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams=set("broadcast-a"),
                clips=Clips(),
                vods=[],
            )
        ],
        set(),
        [],
    ),
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams=set("broadcast-a"),
                clips=Clips(last_day=[clip_a]),
                vods=[vod_a],
            )
        ],
        {"a"},
        [],
    ),
    # Single selected
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams=set("broadcast-a"),
                clips=Clips(last_day=[clip_a]),
                vods=[vod_a],
            )
        ],
        set(),
        [],
    ),
    # Multiple watchable
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams={"broadcast-a"},
                clips=Clips(last_day=[clip_a]),
                vods=[vod_a],
            ),
            Streamer(
                "b",
                "b",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams={"broadcast-b"},
                clips=Clips(last_day=[clip_b]),
                vods=[],
            ),
            Streamer(
                "c",
                "c",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams={"broadcast-c"},
                clips=Clips(),
                vods=[vod_c],
            ),
        ],
        set("d"),
        ["a", "b", "c"],
    ),
    # Multiple mixed
    (
        [
            Streamer(
                "a",
                "a",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams=set(),
                clips=Clips(last_day=[clip_a]),
                vods=[vod_a],
            ),
            Streamer(
                "b",
                "b",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams={"broadcast-b"},
                clips=Clips(last_day=[clip_b]),
                vods=[vod_b],
            ),
            Streamer(
                "c",
                "c",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams={"broadcast-c"},
                clips=Clips(last_week=[clip_c]),
                vods=[],
            ),
            Streamer(
                "d",
                "d",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=True,
                watch_streak_missed_streams={"broadcast-d"},
                clips=Clips(last_day=[clip("d")]),
                vods=[vod_d],
            ),
            Streamer(
                "e",
                "e",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams={"broadcast-e"},
                clips=Clips(last_day=[clip("e")]),
                vods=[vod("e")],
            ),
            Streamer(
                "f",
                "f",
                settings=StreamerSettings(watch_streak=True),
                channel_points_enabled=True,
                is_online=False,
                watch_streak_missed_streams={"broadcast-f"},
                clips=Clips(last_day=[clip("f")]),
                vods=[],
            ),
        ],
        {"d", "e"},
        ["b", "c", "f"],
    ),
]


@pytest.mark.parametrize(
    "streamers,currently_watching,expected", test_select_streamers_data
)
def test_select_streamers(
    streamers: list[Streamer], currently_watching: set[str], expected: list[str]
):
    twitch = MagicMock()
    twitch.vod_viewable = lambda s, v: True

    runner = MagicMock()
    runner.has_context = lambda s: s.channel_id in currently_watching

    recovery = BasicWatchStreakRecovery(
        twitch=twitch, streamers=streamers, runner=runner, config=BasicConfiguration()
    )
    # Setup watching
    for _id in currently_watching:
        recovery._queue.put_nowait(Streamer(_id, _id))
        recovery._queued.add(_id)

    selected = list(recovery.select_streamers())
    assert len(selected) == len(expected)
    for streamer, expected_streamer in zip(selected, expected):
        assert streamer.channel_id == expected_streamer


@pytest.mark.parametrize("streamer,clip,clip_result,expected", test_recover_clip_data)
def test_recover_clip(streamer: Streamer, clip, clip_result, expected):
    twitch = MagicMock()
    twitch.simulate_clip_playback.return_value = clip_result
    recovery = BasicWatchStreakRecovery(
        twitch=twitch,
        streamers=[],
        config=BasicConfiguration(
            max_clip_watch_seconds=1,
            max_vod_watch_seconds=1,
        ),
        runner=MagicMock(),
    )
    recovery.get_clip = MagicMock()
    recovery.get_clip.return_value = clip

    assert recovery.recover_clip(streamer) == expected


test_recover_vod_data = [
    # No vod
    (Streamer("a"), None, False, False),
    # Vod failed
    (Streamer("a"), vod_a, False, False),
    # Vod success
    (Streamer("a"), vod_a, True, True),
]


@pytest.mark.parametrize("streamer,vod,vod_result,expected", test_recover_vod_data)
def test_recover_vod(streamer: Streamer, vod, vod_result, expected):
    twitch = MagicMock()
    twitch.simulate_vod_playback.return_value = vod_result
    recovery = BasicWatchStreakRecovery(
        twitch=twitch,
        streamers=[],
        config=BasicConfiguration(
            max_clip_watch_seconds=1,
            max_vod_watch_seconds=1,
        ),
        runner=MagicMock(),
    )
    recovery.get_vod = MagicMock()
    recovery.get_vod.return_value = vod

    assert recovery.recover_vod(streamer) == expected


test_recover_data = [
    (False, False, "failed"),
    (False, True, "vod"),
    (True, False, "clip"),
    (True, True, "clip"),
]


@pytest.mark.parametrize("clip_result,vod_result,expected", test_recover_data)
def test_recover(clip_result, vod_result, expected):
    recovery = BasicWatchStreakRecovery(
        twitch=MagicMock(),
        streamers=[],
        config=BasicConfiguration(
            max_clip_watch_seconds=1,
            max_vod_watch_seconds=1,
        ),
        runner=MagicMock(),
    )

    recovery.recover_clip = MagicMock()
    recovery.recover_clip.return_value = clip_result
    recovery.recover_vod = MagicMock()
    recovery.recover_vod.return_value = vod_result

    assert recovery.attempt_recovery(MagicMock()) == expected


test_enqueue_data = [
    (False, Streamer("a"), True),
    (True, Streamer("a"), False),
]


@pytest.mark.parametrize("in_queue,streamer,expect_queued", test_enqueue_data)
def test_enqueue(in_queue, streamer, expect_queued):
    recovery = BasicWatchStreakRecovery(
        twitch=MagicMock(),
        streamers=[],
        config=BasicConfiguration(
            max_clip_watch_seconds=1,
            max_vod_watch_seconds=1,
        ),
        runner=MagicMock(),
    )
    recovery._queued = MagicMock()
    recovery._queued.__contains__ = MagicMock()
    recovery._queued.__contains__.return_value = in_queue
    recovery._queue = MagicMock()

    recovery.enqueue(streamer)

    if expect_queued:
        recovery._queue.put.assert_called_once_with(streamer)
        recovery._queued.add.assert_called_once_with(streamer.channel_id)
    else:
        recovery._queue.put.assert_not_called()
        recovery._queued.add.assert_not_called()


streamer_a = Streamer("a", "a")
streamer_b = Streamer("b", "b")
streamer_c = Streamer("c", "c")
streamer_d = Streamer("d", "d")

test_dequeue_data = [
    ([], None),
    ([streamer_a], streamer_a),
    ([streamer_a, streamer_b, streamer_c, streamer_d], streamer_a),
    ([streamer_d, streamer_c, streamer_b, streamer_a], streamer_d),
]


@pytest.mark.parametrize("streamers,expected", test_dequeue_data)
def test_dequeue(streamers: list[Streamer], expected):
    recovery = BasicWatchStreakRecovery(
        twitch=MagicMock(),
        streamers=[],
        config=BasicConfiguration(
            max_clip_watch_seconds=1,
            max_vod_watch_seconds=1,
        ),
        runner=MagicMock(),
    )
    for streamer in streamers:
        recovery.enqueue(streamer)

    assert recovery.dequeue() == expected


def test_process_result():
    # Currently nothing to test
    pass


test__run_data = [
    ([], [], 0, 1, 0, 0),
    ([Streamer("a", "a")], [], 0, 1, 0, 0),
    ([Streamer("a", "a")], [0], 0, 1, 0, 0),
    ([Streamer("a", "a")], [0], 1, 2, 1, 1),
    ([Streamer("a", "a"), Streamer("b", "b")], [1], 2, 2, 2, 1),
    ([Streamer("a", "a"), Streamer("b", "b")], [0, 1], 1, 2, 1, 1),
]


@pytest.mark.parametrize(
    "selected,queued,free_slots,expected_has_free_slot_calls,expected_dequeue_calls,expected_start_task_calls",
    test__run_data,
)
def test__run(
    selected: list[Streamer],
    queued: list[int],
    free_slots: int,
    expected_has_free_slot_calls: int,
    expected_dequeue_calls: int,
    expected_start_task_calls: int,
):
    runner = MagicMock()
    runner.has_free_slot.side_effect = [True for _ in range(free_slots)] + [False]
    runner.start_task.side_effect = [True for _ in range(free_slots)] + [False]

    recovery = BasicWatchStreakRecovery(twitch=MagicMock(), streamers=[], runner=runner)
    recovery.select_streamers = MagicMock()
    recovery.select_streamers.return_value = (s for s in selected)
    recovery.enqueue = MagicMock()
    recovery.dequeue = MagicMock()
    recovery.dequeue.side_effect = [selected[index] for index in queued] + [None]

    recovery._run()

    assert recovery.enqueue.call_count == len(selected)
    assert runner.has_free_slot.call_count == expected_has_free_slot_calls
    assert recovery.dequeue.call_count == expected_dequeue_calls
    assert runner.start_task.call_count == expected_start_task_calls


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
    )
    recovery._run = MagicMock()

    recovery.run()

    assert recovery._run.call_count == 2
