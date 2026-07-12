import logging
from itertools import chain
from queue import Empty, Queue
from threading import Thread

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep

logger = logging.getLogger(__name__)


class WatchStreakRecovery(Thread):
    def __init__(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        max_clip_watch_seconds: float,
        max_vod_watch_seconds: float,
    ):
        super().__init__()
        self.twitch = twitch
        self.streamers = streamers
        self.max_clip_watch_seconds = max_clip_watch_seconds
        self.max_vod_watch_seconds = max_vod_watch_seconds
        self._queue = Queue[Streamer]()
        self._queued = set[str]()

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

    def recover(self, streamer: Streamer):
        """
        Attempts to recover the Watch Streak of the given Streamer by first trying to play back a Clip. If that fails,
        a VOD will then be tried.
        :param streamer: The Streamer to attempt to recover.
        :return: The result.
        """
        if self.recover_clip(streamer):
            return "clip"
        elif self.recover_vod(streamer):
            return "vod"
        else:
            return "failed"

    def enqueue(self, streamer: Streamer):
        """
        Queues the given Streamer for Watch Streak recovery (if not already queued).
        :param streamer: The Streamer to queue.
        """
        if streamer.channel_id not in self._queued:
            logger.debug(f"Queueing {streamer} for Watch Streak recovery")
            self._queue.put(streamer)
            self._queued.add(streamer.channel_id)

    def run(self):
        while self.twitch.running:
            logger.debug(f"Checking for missing Watch Streaks")
            for streamer in self.streamers:
                if streamer.needs_watch_streak_recovery():
                    self.enqueue(streamer)
            try:
                streamer = self._queue.get(timeout=1)
                try:
                    result = self.recover(streamer)
                    logger.debug(f"Streak Recovery: {result}")

                except Exception as e:
                    logger.error(f"Exception in WatchStreakRecovery: {e}")
                finally:
                    self._queued.remove(streamer.channel_id)
            except Empty:
                pass

            interruptible_sleep(lambda: self.twitch.running, duration=20)
