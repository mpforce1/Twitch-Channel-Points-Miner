import logging
import time
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from itertools import islice
from threading import Thread
from typing import TypedDict

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep

logger = logging.getLogger(__name__)


class Result(TypedDict):
    success: bool
    reason: str


class Slot:
    def __init__(self, streamer: Streamer, future: Future[Result], start_time: float):
        self.streamer = streamer
        self.future = future
        self.start_time = start_time


class WeeklyRewardsProgressor(Thread):
    """Attempts to progress Weekly Rewards by watching Clips and VODs."""

    def __init__(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        max_concurrent_watch: int = 2,
        max_seconds_clips: float = 30,
        max_seconds_vods: float = 8 * 60,
        loop_interval_seconds: float = 20,
    ):
        super().__init__(target=self.watch_loop, name="Weekly Rewards Progressor")
        self.twitch = twitch
        """ The Twitch API instance. """
        self.streamers = streamers
        """ The Streamers to monitor. """
        if max_concurrent_watch <= 0:
            raise ValueError(
                f"max_concurrent_watch must be greater than 0: {max_concurrent_watch}"
            )
        self.max_concurrent_watch = max_concurrent_watch
        """ The maximum amount to watch concurrently. """
        self.max_seconds_clips = max_seconds_clips
        """ The maximum amount of time to wait for watching a clip to trigger progress. """
        self.max_seconds_vods = max_seconds_vods
        """ The maximum amount of time to watch a vod. """
        self.loop_interval_seconds = loop_interval_seconds
        """ The amount of seconds in between iterations of the watch loop. """
        self._full_timeout = self.max_seconds_vods + self.max_seconds_clips + 10

    def select_streamers(self, watching: set[str]):
        """
        Selects Streamers to attempt to progress.
        :return: The Streamers.
        """
        target_streamers = list(
            streamer
            for streamer in self.streamers
            # Don't watch VODs for streamers that are online, we may be able to advance via watching live
            if streamer.is_online is False
            # Only watch VODs for streamers that are missing the reward
            and streamer.missing_weekly_reward()
            # Only try and watch streamers that have a Clip or VOD available
            and (
                self.get_clip(streamer) is not None
                or self.get_vod(streamer) is not None
            )
            # Only select streamers that aren't currently being watched
            and streamer.channel_id not in watching
        )
        return list(islice(target_streamers, self.max_concurrent_watch - len(watching)))

    def get_clip(self, streamer: Streamer):
        top_clips = streamer.clips
        if len(top_clips) == 0:
            logger.debug(f"No Clip available for {streamer}")
            return None
        for clip in top_clips:
            if clip.duration_seconds > 5:
                return clip
            else:
                logger.debug(
                    f"Rejecting Clip {clip.title}, it's shorter than 5 seconds ({clip.duration_seconds}s)"
                )
        logger.debug(f"All {len(top_clips)} Clips are too short")
        return None

    def get_vod(self, streamer: Streamer):
        recent_broadcasts = streamer.vods
        if recent_broadcasts is None or len(recent_broadcasts) == 0:
            logger.debug(f"No VOD available for {streamer}")
            return None
        for video in recent_broadcasts:
            if not self.twitch.vod_viewable(streamer, video):
                logger.debug(
                    f"rejecting VOD {video.edge.id}, it's not viewable (probably subscriber-only)"
                )
                continue
            vod = video.edge
            if vod.length_seconds < 6 * 60:
                logger.debug(
                    f"Rejecting VOD {vod.id}, it's shorter than 6 minutes ({vod.length_seconds}s)"
                )
            else:
                return vod
        logger.debug(f"All {len(recent_broadcasts)} recent VODs too short")
        return None

    def do_watch(self, streamer: Streamer) -> Result:
        """
        Attempts to watch a Clip/VOD for the given Streamer.
        :param streamer: The Streamer to watch.
        :return: A result.
        """
        clip = self.get_clip(streamer)
        if clip is not None and self.twitch.simulate_clip_playback(
            streamer, clip, max_watch_seconds=self.max_seconds_clips
        ):
            return Result(success=True, reason="clip")
        if not self.twitch.running:
            return Result(success=False, reason="miner not running")
        vod = self.get_vod(streamer)
        if vod is not None and self.twitch.simulate_vod_playback(
            streamer, vod, max_watch_seconds=self.max_seconds_vods
        ):
            return Result(success=True, reason="vod")
        if not self.twitch.running:
            return Result(success=False, reason="miner not running")
        if clip is None:
            if vod is None:
                return Result(success=False, reason="streamer has no clips or vods")
            else:
                return Result(success=False, reason="vod timed out")
        if vod is None:
            return Result(
                success=False, reason="clip timed out and streamer has no viewable vods"
            )
        return Result(success=False, reason="clip and vod both timed out")

    def process_result(self, streamer: Streamer, result: Result):
        """
        Processes a result of a watch attempt.
        :param streamer: The Streamer we attempted to watch.
        :param result: The result to process.
        """
        if result["success"]:
            logger.info(
                f"Weekly Reward obtained for {streamer} via {result["reason"]}",
                extra={"emoji": ":grinning_face:"},
            )
        else:
            logger.error(
                f"Unable to progress Weekly Reward for {streamer} with Clips or VODs: {result["reason"]}",
            )

    # Watch a single streamer, process the result, and handle errors
    def watch_single(self, streamer: Streamer):
        """
        Watches a single Streamer, processes the result, and handles any errors.
        :param streamer: The Streamer to watch.
        """
        try:
            self.process_result(streamer, self.do_watch(streamer))
        except Exception as e:
            logger.error(f"Error when trying to get Weekly Reward for {streamer}: {e}")

    def manage_slots(self, slots: list[Slot | None]):
        for slot_index in range(len(slots)):
            slot = slots[slot_index]
            if slot is not None:
                try:
                    if slot.future.done():
                        slots[slot_index] = None
                        self.process_result(slot.streamer, slot.future.result())
                    elif time.monotonic() - slot.start_time > self._full_timeout:
                        slots[slot_index] = None
                        logger.error(
                            f"Unable to get Weekly Reward for {slot.streamer}, took more than {self._full_timeout} seconds",
                        )
                        slot.future.cancel()
                except Exception as e:
                    logger.error(
                        f"Error when trying to get Weekly Reward for {slot.streamer}: {e}"
                    )

    def watch_multiple(self, thread_pool: ThreadPoolExecutor, slots: list[Slot | None]):
        # Select new streamers to watch
        target_streamers = self.select_streamers(
            set(slot.streamer.channel_id for slot in slots if slot is not None)
        )
        # When there are no targets we don't need to do anything
        if len(target_streamers) == 0:
            pass
        # When there's only 1 target and all slots are empty, we can do this inline sync
        elif len(target_streamers) == 1 and all(slot is None for slot in slots):
            self.watch_single(target_streamers[0])
        # When there's at least 1 target and at least 1 filled slot we must use the slots
        elif len(target_streamers) > 1 and any(slot is None for slot in slots):
            for streamer, index in zip(
                target_streamers,
                (index for index in range(len(slots)) if slots[index] is None),
            ):
                slots[index] = Slot(
                    streamer,
                    thread_pool.submit(self.do_watch, streamer),
                    time.monotonic(),
                )

    def watch_loop(self):
        """
        Periodically checks all Streamers weekly reward status and attempts to watch Clips/VODs for those that haven't
        yet advanced theirs today/this week.
        """
        # When max concurrent is 1 we don't need a thread pool
        if self.max_concurrent_watch == 1:
            while self.twitch.running:
                target_streamers = self.select_streamers(set())
                if len(target_streamers) > 0:
                    self.watch_single(target_streamers[0])
                interruptible_sleep(
                    running_flag=lambda: self.twitch.running,
                    duration=self.loop_interval_seconds,
                )
        else:
            with ThreadPoolExecutor(
                max_workers=self.max_concurrent_watch,
                thread_name_prefix="weekly_reawrds_watcher",
            ) as thread_pool:
                slots: list[Slot | None] = [
                    None for _ in range(self.max_concurrent_watch)
                ]
                while self.twitch.running:
                    self.manage_slots(slots)
                    self.watch_multiple(thread_pool, slots)
                    interruptible_sleep(
                        running_flag=lambda: self.twitch.running,
                        duration=self.loop_interval_seconds,
                    )
