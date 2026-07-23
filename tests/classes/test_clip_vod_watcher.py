import time
from typing import Any
from typing import Callable
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.ClipVodWatcher import (
    BasicClipVodWatcher,
    BasicConfiguration,
    Result,
)
from TwitchChannelPointsMiner.classes.SlottedTaskRunner import SlottedTaskRunner
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, Clips
from TwitchChannelPointsMiner.classes.entities.Video import Video
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip
from TwitchChannelPointsMiner.classes.gql.data.response.FilterableVideoTower import (
    VideoEdge,
)


class TestingClipVodWatcher(BasicClipVodWatcher):
    def __init__(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        runner: SlottedTaskRunner,
        config: BasicConfiguration | None = None,
        get_clip: Callable[[Streamer], Clip | None] | None = None,
        get_vod: Callable[[Streamer], Video | None] | None = None,
        can_watch: Callable[[Streamer], bool] | None = None,
    ):
        super().__init__(twitch, streamers, runner, config)
        self._get_clip = get_clip if get_clip else lambda s: None
        self._get_vod = get_vod if get_vod else lambda s: None
        self._can_watch = can_watch if can_watch else lambda s: True

    def get_clip(self, streamer: Streamer) -> Clip | None:
        return self._get_clip(streamer)

    def get_vod(self, streamer: Streamer) -> Video | None:
        return self._get_vod(streamer)

    def can_watch(self, streamer: Streamer) -> bool:
        return self._can_watch(streamer)


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


def vod(_id: str):
    return Video(
        edge=VideoEdge(_id=_id, broadcast_id=f"broadcast-{_id}", length_seconds=1)
    )


vod_a = vod("a")
vod_b = vod("b")
vod_c = vod("c")
vod_d = vod("d")

test_select_streamers_data = [
    # None
    ([], set(), set(), []),
    ([], {"a", "b"}, {"c", "d"}, []),
    # Single streamer, never selected
    #  On cooldown
    (
        [Streamer("a", "a")],
        set(),
        {"a"},
        [],
    ),
    #  In runner/queue
    (
        [Streamer("a", "a")],
        {"a"},
        set(),
        [],
    ),
    #  No Clips/VODs
    (
        [Streamer("a", "a")],
        set(),
        set(),
        [],
    ),
    # Single selected
    (
        [Streamer("a", "a", clips=Clips(last_day=[clip_a]))],
        set(),
        set(),
        ["a"],
    ),
    (
        [Streamer("a", "a", vods=[vod_a])],
        set(),
        set(),
        ["a"],
    ),
    (
        [
            Streamer(
                "a",
                "a",
                clips=Clips(last_day=[clip_a]),
                vods=[vod_a],
            )
        ],
        set(),
        set(),
        ["a"],
    ),
    # Multiple watchable
    (
        [
            Streamer("a", "a", clips=Clips(last_day=[clip_a])),
            Streamer("b", "b", vods=[vod_b]),
            Streamer("c", "c", clips=Clips(last_day=[clip_c]), vods=[vod_c]),
        ],
        {"d"},
        {"e"},
        ["a", "b", "c"],
    ),
    # Multiple mixed
    (
        [
            Streamer(
                "a",
                "a",
            ),
            Streamer("b", "b", clips=Clips(last_day=[clip_b])),
            Streamer("c", "c", vods=[vod_c]),
            Streamer("d", "d", clips=Clips(last_day=[clip("d")]), vods=[vod("d")]),
            Streamer("e", "e", clips=Clips(last_day=[clip("e")]), vods=[vod("e")]),
            Streamer("f", "f", clips=Clips(last_day=[clip("f")])),
        ],
        {"d"},
        {"e"},
        ["b", "c", "f"],
    ),
]


@pytest.mark.parametrize(
    "streamers,watching,cooldowns,expected", test_select_streamers_data
)
def test_select_streamers(
    streamers: list[Streamer],
    watching,
    cooldowns: set[str],
    expected: list[str],
):
    runner = MagicMock()
    runner.has_context = lambda s: s.channel_id in watching

    twitch = MagicMock()
    twitch.vod_viewable = lambda s, v: True

    watcher = TestingClipVodWatcher(
        twitch=twitch,
        streamers=streamers,
        runner=runner,
        get_clip=lambda s: s.clips.last_day[0] if len(s.clips.last_day) > 0 else None,
        get_vod=lambda s: s.vods[0] if len(s.vods) > 0 else None,
    )

    # Setup cooldowns
    for _id in cooldowns:
        watcher._cooldowns[_id] = 10

    # Setup watching
    for _id in watching:
        watcher._queue.put_nowait(Streamer(_id, _id))
        watcher._queued.add(_id)

    selected = list(watcher.select_streamers())
    assert len(selected) == len(expected)
    for selected_streamer, expected_streamer_id in zip(selected, expected):
        assert selected_streamer.channel_id == expected_streamer_id


test_watch_clip_data = [
    (Streamer("a"), None, False, Result(success=False, reason="No Clips")),
    (Streamer("a"), clip("a"), False, Result(success=False, reason="Clip timed out")),
    (Streamer("a"), clip("a"), True, Result(success=True, reason="Clip")),
]


@pytest.mark.parametrize(
    "streamer,clip,watch_result,expected_result", test_watch_clip_data
)
def test_watch_clip(
    streamer: Streamer, clip: Clip | None, watch_result, expected_result
):
    twitch = MagicMock()
    twitch.simulate_clip_playback.return_value = watch_result

    watcher = TestingClipVodWatcher(
        twitch=twitch,
        streamers=[],
        runner=MagicMock(),
    )
    watcher.get_clip = lambda streamer: clip

    assert watcher.watch_clip(streamer) == expected_result


test_watch_vod_data = [
    (Streamer("a"), None, False, Result(success=False, reason="No VODs")),
    (Streamer("a"), vod("a"), False, Result(success=False, reason="VOD timed out")),
    (Streamer("a"), vod("a"), True, Result(success=True, reason="VOD")),
]


@pytest.mark.parametrize(
    "streamer,vod,watch_result,expected_result", test_watch_vod_data
)
def test_watch_vod(
    streamer: Streamer, vod: Video | None, watch_result: bool, expected_result: Result
):
    twitch = MagicMock()
    twitch.simulate_vod_playback.return_value = watch_result

    watcher = TestingClipVodWatcher(
        twitch=twitch,
        streamers=[],
        runner=MagicMock(),
    )
    watcher.get_vod = lambda streamer: vod

    assert watcher.watch_vod(streamer) == expected_result


class MockTwitch:
    def __init__(self, running: int):
        self._running = running
        self.running_count = 0

    @property
    def running(self):
        self.running_count += 1
        return self.running_count <= self._running


test_watch_data = [
    (
        Result(success=True, reason="clip test result"),
        False,
        None,
        False,
        Result(success=True, reason="clip test result"),
    ),
    (
        Result(success=False, reason="clip test result"),
        False,
        None,
        False,
        Result(success=False, reason="Miner not running"),
    ),
    (
        Result(success=False, reason="clip test result"),
        True,
        Result(success=True, reason="vod test result"),
        False,
        Result(success=True, reason="vod test result"),
    ),
    (
        Result(success=False, reason="clip test result"),
        True,
        Result(success=False, reason="vod test result"),
        False,
        Result(success=False, reason="Miner not running"),
    ),
    (
        Result(success=False, reason="clip test result"),
        True,
        Result(success=False, reason="vod test result"),
        True,
        Result(success=False, reason="clip test result and vod test result"),
    ),
]


@pytest.mark.parametrize(
    "clip_result,first_running,vod_result,second_running,expected", test_watch_data
)
def test_watch(
    clip_result: Result,
    first_running: bool,
    vod_result: Result,
    second_running: bool,
    expected: Result,
):
    twitch: Any = MockTwitch(first_running + second_running)
    watcher = TestingClipVodWatcher(
        twitch=twitch,
        streamers=[],
        runner=MagicMock(),
    )
    watcher.watch_clip = lambda streamer: clip_result
    watcher.watch_vod = lambda streamer: vod_result

    assert watcher.watch(MagicMock()) == expected


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
    streamer_id: str,
    failures: dict[str, int],
    cooldowns: dict[str, float],
    max_failures_per_streamer: int,
    current_time: float,
    expected_failures: dict[str, int],
    expected_cooldowns: dict[str, float],
):
    watcher = TestingClipVodWatcher(
        twitch=MagicMock(),
        streamers=[],
        runner=MagicMock(),
        config=BasicConfiguration(
            max_failures_per_streamer=max_failures_per_streamer,
        ),
    )
    watcher._failures = failures
    watcher._cooldowns = cooldowns

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(time, "monotonic", lambda: current_time)
        watcher.update_failures(streamer_id)

    assert watcher._failures == expected_failures
    assert watcher._cooldowns == expected_cooldowns


test_process_result_data = [
    (Streamer("a", "a"), Result(success=True, reason=""), False, True, True),
    (Streamer("a", "a"), Result(success=False, reason=""), True, False, False),
]


@pytest.mark.parametrize(
    "streamer,result,expect_call_update_failures,expect_pop_failures,expect_pop_cooldowns",
    test_process_result_data,
)
def test_process_result(
    streamer: Streamer,
    result: Result,
    expect_call_update_failures: bool,
    expect_pop_failures: bool,
    expect_pop_cooldowns: bool,
):
    watcher = TestingClipVodWatcher(
        twitch=MagicMock(),
        streamers=[],
        runner=MagicMock(),
    )
    watcher.update_failures = MagicMock()
    watcher._failures = MagicMock()
    watcher._cooldowns = MagicMock()

    watcher.process_result(streamer, result)

    if expect_call_update_failures:
        watcher.update_failures.assert_called_once_with(streamer.channel_id)
    if expect_pop_failures:
        watcher._failures.pop.assert_called_once_with(streamer.channel_id, None)
    if expect_pop_cooldowns:
        watcher._cooldowns.pop.assert_called_once_with(streamer.channel_id, None)


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


test_manage_cooldowns_data = [
    # Empty cooldowns
    ({}, 0, 1, {}),
    ({}, 1000, 10, {}),
    # Single cooldown
    ({"a": 0}, 0, 10, {"a": 0}),
    ({"a": 10}, 19, 10, {"a": 10}),
    ({"a": 10}, 20, 10, {"a": 10}),
    ({"a": 10}, 21, 10, {}),
    # Multiple cooldowns
    ({"a": 0, "b": 1}, 10, 10, {"a": 0, "b": 1}),
    ({"a": 0, "b": 1}, 11, 10, {"b": 1}),
    ({"a": 0, "b": 1}, 12, 10, {}),
]


@pytest.mark.parametrize(
    "cooldowns,current_time,failure_cooldown_seconds,expected_cooldowns",
    test_manage_cooldowns_data,
)
def test_manage_cooldowns(
    cooldowns: dict[str, float],
    current_time: float,
    failure_cooldown_seconds: float,
    expected_cooldowns: dict[str, float],
):
    watcher = TestingClipVodWatcher(
        twitch=MagicMock(),
        streamers=[],
        runner=MagicMock(),
        config=BasicConfiguration(failure_cooldown_seconds=failure_cooldown_seconds),
    )
    watcher._cooldowns = cooldowns

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(time, "monotonic", lambda: current_time)
        watcher.manage_cooldowns()

    assert watcher._cooldowns == expected_cooldowns


test_enqueue_data = [
    (False, Streamer("a"), True),
    (True, Streamer("a"), False),
]


@pytest.mark.parametrize("in_queue,streamer,expect_queued", test_enqueue_data)
def test_enqueue(in_queue, streamer, expect_queued):
    recovery = TestingClipVodWatcher(
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
    recovery = TestingClipVodWatcher(
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

    recovery = TestingClipVodWatcher(twitch=MagicMock(), streamers=[], runner=runner)
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


def test_run():
    twitch: Any = MockTwitch(4)
    recovery = TestingClipVodWatcher(
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
