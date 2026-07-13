import abc
from dataclasses import dataclass
import logging
from itertools import chain
from queue import Empty, Queue
from threading import Thread

from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunner,
    SlottedTaskRunnerFactory,
)
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep

logger = logging.getLogger(__name__)


class WatchStreakRecovery(abc.ABC, Thread):
    @abc.abstractmethod
    def attempt_recovery(self, streamer: Streamer) -> str:
        """
        Attempts to recover the Watch Streak of the given Streamer.
        :param streamer: The Streamer to attempt to recover.
        :return: The result.
        """
        pass


@dataclass
class BasicConfiguration:
    max_concurrent: int = 3
    max_clip_watch_seconds: float = 30
    max_vod_watch_seconds: float = 8 * 60
    interval_seconds: float = 20


class BasicWatchStreakRecovery(WatchStreakRecovery):
    """Attempts to recover missed Watch Streaks by watching Clips/VODs."""

    def __init__(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        runner: SlottedTaskRunner,
        config: BasicConfiguration | None = None,
    ):
        super().__init__()
        self.twitch = twitch
        """The Twitch API instance."""
        self.streamers = streamers
        """The Streamers to check for recovery."""
        if config is None:
            config = BasicConfiguration()
        self.max_clip_watch_seconds = config.max_clip_watch_seconds
        """The maximum number of seconds to watch a Clip."""
        self.max_vod_watch_seconds = config.max_vod_watch_seconds
        """The maximum number of seconds to watch a VOD."""
        self.runner = runner
        """The runner that can run progression tasks."""
        self.interval_seconds = config.interval_seconds
        """The interval between checking for streamers with recoverable streaks."""
        self._queue = Queue[Streamer]()
        self._queued = set[str]()
        self._total_timeout = (
            config.max_clip_watch_seconds + config.max_vod_watch_seconds + 5
        )

    def get_clip(self, streamer: Streamer):
        """
        Tries to get a Clip for the given Streamer from one of the missed broadcasts.
        :param streamer: The Streamer for which to find the Clip.
        :return: The Clip or None if one couldn't be found.
        """
        if len(streamer.watch_streak_missed_streams) > 0:
            # It might be possible to recover using clips from last_week if we're right on the edge of the grace period
            for clip in chain(streamer.clips.last_day, streamer.clips.last_week):
                if (
                    clip.broadcast_id is not None
                    and clip.broadcast_id in streamer.watch_streak_missed_streams
                ):
                    return clip
        return None

    def get_vod(self, streamer: Streamer):
        """
        Tries to get a VOD for the given Streamer that matches one of the missed broadcast ids.
        :param streamer: The Streamer for which to find the VOD.
        :return: The VOD or None if one couldn't be found.
        """
        if len(streamer.watch_streak_missed_streams) > 0:
            # We can match these with the exact VOD, nothing else will work
            for vod in streamer.vods:
                if (
                    vod.edge.broadcast_id in streamer.watch_streak_missed_streams
                    and self.twitch.vod_viewable(streamer, vod)
                ):
                    return vod
        return None

    def recover_clip(self, streamer: Streamer):
        """
        Attempts to recover the Watch Streak of the given Streamer by playing back a Clip.
        :param streamer: The Streamer to attempt to recover.
        :return: True if the Streak was recovered, False otherwise.
        """
        logger.debug(f"Processing {streamer}: looking up recent Clip")
        clip = self.get_clip(streamer)
        if clip is None:
            logger.debug(f"No Clip available for {streamer}")
            return False
        result = self.twitch.simulate_clip_playback(
            streamer,
            clip,
            max_watch_seconds=self.max_clip_watch_seconds,
            done=lambda s: not s.has_missed_streams(),
        )
        if result:
            logger.debug(f"Finished Clip watch for {streamer}: able to recover")
            return True
        else:
            logger.debug(f"Finished Clip watch for {streamer}: unable to recover")
            return False

    def recover_vod(self, streamer: Streamer):
        """
        Attempts to recover the Watch Streak of the given Streamer by playing back a VOD.
        :param streamer: The Streamer to attempt to recover.
        :return: True if the Streak was recovered, False otherwise.
        """
        logger.debug(f"Processing {streamer}: looking up recent VOD")
        vod = self.get_vod(streamer)
        if vod is None:
            logger.debug(f"No VOD available for {streamer}, cannot recover streak")
            return False
        result = self.twitch.simulate_vod_playback(
            streamer,
            vod.edge,
            max_watch_seconds=self.max_vod_watch_seconds,
            done=lambda s: not s.has_missed_streams(),
        )
        if result:
            logger.debug(f"Finished VOD watch for {streamer}: able to recover")
            return True
        else:
            logger.debug(f"Finished VOD watch for {streamer}: unable to recover")
            return False

    def attempt_recovery(self, streamer: Streamer):
        if self.recover_clip(streamer):
            return "clip"
        elif self.recover_vod(streamer):
            return "vod"
        else:
            return "failed"

    def _recover_lambda(self, streamer: Streamer):
        return lambda: self.attempt_recovery(streamer)

    def enqueue(self, streamer: Streamer):
        """
        Queues the given Streamer for Watch Streak recovery (if not already queued).
        :param streamer: The Streamer to queue.
        """
        if streamer.channel_id not in self._queued:
            logger.debug(f"Queueing {streamer} for Watch Streak recovery")
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

    def process_result(self, streamer: Streamer, result: str):
        """
        Processes the result of a recovery attempt.
        :param streamer: The Streamer for the attempt.
        :param result: The result of the attempt.
        """
        logger.debug(f"Streak Recovery for {streamer}: {result}")

    def _run(self):
        for streamer in self.streamers:
            if streamer.needs_watch_streak_recovery():
                self.enqueue(streamer)
        while self.runner.has_free_slot():
            streamer = self.dequeue()
            if streamer is not None:
                logger.debug(f"Beginning recovery task for {streamer}")
            if streamer is None or not self.runner.start_task(
                streamer,
                self._recover_lambda(streamer),
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


class WatchStreakRecoveryFactory(abc.ABC):
    @abc.abstractmethod
    def create(self, twitch: Twitch, streamers: list[Streamer]) -> WatchStreakRecovery:
        pass


class BasicWatchStreakRecoveryFactory(WatchStreakRecoveryFactory):
    def __init__(
        self,
        runner_factory: SlottedTaskRunnerFactory,
        config: BasicConfiguration | None = None,
    ):
        self.config = config
        self.runner_factory = runner_factory

    def create(self, twitch: Twitch, streamers: list[Streamer]) -> WatchStreakRecovery:
        runner = self.runner_factory.create(twitch, "Watch Streak Recovery")
        return BasicWatchStreakRecovery(
            twitch=twitch, streamers=streamers, runner=runner, config=self.config
        )
