import abc
from dataclasses import dataclass
import logging
from queue import Empty, Queue
from threading import Thread
import time
from typing import Generator, TypedDict

from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunner,
)
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.Video import Video
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep

logger = logging.getLogger(__name__)


class Result(TypedDict):
    success: bool
    reason: str


class ClipVodWatcher(abc.ABC, Thread):
    @abc.abstractmethod
    def watch(self, streamer: Streamer) -> Result:
        """
        Watches a Clip, then potentially a VOD for the given Streamer.
        :param streamer: The Streamer to watch.
        :return: The result.
        """
        pass

    @abc.abstractmethod
    def enqueue(self, streamer: Streamer):
        """
        Queues the given Streamer for watching (if not already queued).
        :param streamer: The Streamer to queue.
        """
        pass


@dataclass
class BasicConfiguration:
    max_concurrent: int = 3
    max_clip_watch_seconds: float = 30
    max_vod_watch_seconds: float = 8 * 60
    interval_seconds: float = 20
    max_failures_per_streamer: int = 1
    failure_cooldown_seconds: float = 60 * 60


class BasicClipVodWatcher(ClipVodWatcher, abc.ABC):
    """Attempts to watch a Clips (then maybe a VOD) for Streamers."""

    def __init__(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        runner: SlottedTaskRunner[Streamer, Result],
        config: BasicConfiguration | None = None,
    ):
        super().__init__()
        """The name of this watcher."""
        self.twitch = twitch
        """The Twitch API instance."""
        self.streamers = streamers
        """The Streamers."""
        if config is None:
            config = BasicConfiguration()
        self.max_clip_watch_seconds = config.max_clip_watch_seconds
        """The maximum number of seconds to watch a Clip."""
        self.max_vod_watch_seconds = config.max_vod_watch_seconds
        """The maximum number of seconds to watch a VOD."""
        self.runner = runner
        """The runner that can run watch tasks."""
        self.interval_seconds = config.interval_seconds
        """The interval between checking for watchable Streamers."""
        self.max_failures_per_streamer = config.max_failures_per_streamer
        """ The maximum number of failed attempt to do per streamer before putting them into a cooldown. """
        self.failure_cooldown_seconds = config.failure_cooldown_seconds
        """ The amount of seconds to wait after failing to watch `max_attempts_per_streamer` times for a Streamer. """
        self._queue = Queue[Streamer]()
        self._queued = set[str]()
        self._total_timeout = (
            config.max_clip_watch_seconds + config.max_vod_watch_seconds + 5
        )
        self._failures = dict[str, int]()
        self._cooldowns = dict[str, float]()

    @abc.abstractmethod
    def get_clip(self, streamer: Streamer) -> Clip | None:
        """
        Tries to get a Clip for the given Streamer.
        :param streamer: The Streamer for which to find the Clip.
        :return: The Clip or None if one couldn't be found.
        """
        pass

    @abc.abstractmethod
    def get_vod(self, streamer: Streamer) -> Video | None:
        """
        Tries to get a VOD for the given Streamer.
        :param streamer: The Streamer for which to find the VOD.
        :return: The VOD or None if one couldn't be found.
        """
        pass

    @abc.abstractmethod
    def can_watch(self, streamer: Streamer) -> bool:
        """
        Gets whether the given Streamer can be watched.
        :param streamer: The Streamer to check.
        :return: True if the Streamer can be watched, False otherwise.
        """
        pass

    def done_watching(self, streamer: Streamer) -> bool:
        """
        Gets whether we can finish watching a Streamer early.
        :param streamer: The Streamer to watch.
        :return: True if we can finish early, False otherwise.
        """
        return not self.can_watch(streamer)

    def select_streamers(self) -> Generator[Streamer, None, None]:
        """
        Selects Streamers to attempt to watch.
        :return: The Streamers.
        """
        return (
            streamer
            for streamer in self.streamers
            # Avoid streamers that are on cooldown
            if streamer.channel_id not in self._cooldowns
            # Avoid streamers currently being watched
            and not self.runner.has_context(streamer)
            # Avoid streamers currently queued to watch
            and streamer.channel_id not in self._queued
            # Avoid streamers not matching subclass criteria
            and self.can_watch(streamer)
            # Avoid streamers that don't have either a valid Clip or VOD
            and (
                self.get_clip(streamer) is not None
                or self.get_vod(streamer) is not None
            )
        )

    def watch_clip(self, streamer: Streamer) -> Result:
        """
        Attempts to watch a Clip of the given Streamer.
        :param streamer: The Streamer to attempt to watch.
        :return: The watch Result.
        """
        logger.debug(f"Processing {streamer}: selecting Clip")
        clip = self.get_clip(streamer)
        if clip is None:
            logger.debug(f"No Clip available for {streamer}")
            return Result(success=False, reason="No Clips")
        result = self.twitch.simulate_clip_playback(
            streamer,
            clip,
            max_watch_seconds=self.max_clip_watch_seconds,
            done=lambda s: self.done_watching(s),
        )
        logger.debug(
            f"Finished Clip watch for {streamer}: {'Success' if result else 'Failure'}"
        )
        return Result(success=result, reason="Clip" if result else "Clip timed out")

    def watch_vod(self, streamer: Streamer) -> Result:
        """
        Attempts to watch a VOD of the given Streamer.
        :param streamer: The Streamer to attempt to watch.
        :return: The watch Result.
        """
        logger.debug(f"Processing {streamer}: selecting VOD")
        vod = self.get_vod(streamer)
        if vod is None:
            logger.debug(f"No VOD available for {streamer}")
            return Result(success=False, reason="No VODs")
        result = self.twitch.simulate_vod_playback(
            streamer,
            vod.edge,
            max_watch_seconds=self.max_vod_watch_seconds,
            done=lambda s: self.done_watching(s),
        )
        logger.debug(
            f"Finished VOD watch for {streamer}: {'Success' if result else 'Failure'}"
        )
        return Result(success=result, reason="VOD" if result else "VOD timed out")

    def watch(self, streamer: Streamer) -> Result:
        """
        Watches a Clip and/or VOD for the given Streamer.
        :param streamer: The Streamer to watch.
        :return: The Result.
        """
        clip_result = self.watch_clip(streamer)
        if clip_result["success"]:
            return clip_result
        if not self.twitch.running:
            return Result(success=False, reason="Miner not running")
        vod_result = self.watch_vod(streamer)
        if vod_result["success"]:
            return vod_result
        if not self.twitch.running:
            return Result(success=False, reason="Miner not running")
        return Result(
            success=False, reason=f"{clip_result['reason']} and {vod_result['reason']}"
        )

    def _watch_lambda(self, streamer: Streamer):
        return lambda: self.watch(streamer)

    def update_failures(self, streamer_id: str):
        """
        Increments the number of failures for the given streamer. If the number of failures exceeds the maximum the
        streamer will be put on cooldown.
        :param streamer_id: The id of the Streamer.
        """
        failures = self._failures.get(streamer_id, 0) + 1
        if failures >= self.max_failures_per_streamer:
            self._cooldowns[streamer_id] = time.monotonic()
            self._failures.pop(streamer_id, None)
        else:
            self._failures[streamer_id] = failures

    def process_result(self, streamer: Streamer, result: Result):
        """
        Processes the result of a watch attempt.
        :param streamer: The Streamer for the attempt.
        :param result: The result of the attempt.
        """
        if result["success"]:
            self._failures.pop(streamer.channel_id, None)
            self._cooldowns.pop(streamer.channel_id, None)
        else:
            self.update_failures(streamer.channel_id)

    def manage_cooldowns(self):
        """Checks the cooldowns list and removes items that have been on cooldown long enough."""
        for streamer_id in list(self._cooldowns.keys()):
            start_time = self._cooldowns[streamer_id]
            if (time.monotonic() - start_time) > self.failure_cooldown_seconds:
                self._cooldowns.pop(streamer_id)

    def enqueue(self, streamer: Streamer):
        """
        Queues the given Streamer for watching (if not already queued).
        :param streamer: The Streamer to queue.
        """
        if streamer.channel_id not in self._queued:
            logger.debug(f"Queueing {streamer} to watch")
            self._queue.put(streamer)
            self._queued.add(streamer.channel_id)

    def dequeue(self) -> Streamer | None:
        """
        Tries to get the next Streamer from the queue.
        :return: The next Streamer or None if the queue is empty.
        """
        try:
            streamer = self._queue.get_nowait()
            self._queued.remove(streamer.channel_id)
            return streamer
        except (Empty, KeyError):
            # Empty means the queue is empty, KeyError means we're out of sync
            return None

    def _run(self):
        # Ensure cooldowns are updated
        self.manage_cooldowns()
        # Enqueue Streamers
        for streamer in self.select_streamers():
            self.enqueue(streamer)
        # Create watch tasks until all slots are full
        while self.runner.has_free_slot():
            streamer = self.dequeue()
            if streamer is not None:
                logger.debug(f"Beginning watch task for {streamer}")
            if streamer is None or not self.runner.start_task(
                streamer,
                self._watch_lambda(streamer),
                self._total_timeout,
                on_complete=self.process_result,
            ):
                break

    def run(self):
        while self.twitch.running:
            self._run()
            interruptible_sleep(
                lambda: self.twitch.running, duration=self.interval_seconds
            )
