import abc
import logging
import time
from dataclasses import dataclass
from threading import Thread
from typing import TypedDict

from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunner,
    SlottedTaskRunnerFactory,
)
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep

logger = logging.getLogger(__name__)


class Result(TypedDict):
    success: bool
    reason: str


class WeeklyRewardsProgressor(abc.ABC, Thread):
    """Attempts to progress Weekly Rewards."""
    @abc.abstractmethod
    def attempt_progress(self, streamer: Streamer) -> Result:
        """
        Attempts to make progress for the Weekly Rewards for the given Streamer.
        :param streamer: The Streamer to progress.
        :return: The result.
        """
        pass


@dataclass
class BasicConfiguration:
    max_concurrent_watch: int = 2
    max_seconds_clips: float = 30
    max_seconds_vods: float = 8 * 60
    loop_interval_seconds: float = 20
    max_failures_per_streamer: int = 1
    failure_cooldown_seconds: float = 60 * 60


class BasicWeeklyRewardsProgressor(WeeklyRewardsProgressor):
    """Attempts to progress Weekly Rewards by watching Clips and VODs."""

    def __init__(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        runner: SlottedTaskRunner[Streamer, Result],
        config: BasicConfiguration | None = None,
    ):
        super().__init__(name="Weekly Rewards Progressor")
        self.twitch = twitch
        """ The Twitch API instance. """
        self.streamers = streamers
        """ The Streamers to monitor. """
        self.runner = runner
        """ The runner used to manage concurrent watching. """
        if config is None:
            config = BasicConfiguration()
        """ The maximum amount to watch concurrently. """
        self.max_seconds_clips = config.max_seconds_clips
        """ The maximum amount of time to wait for watching a clip to trigger progress. """
        self.max_seconds_vods = config.max_seconds_vods
        """ The maximum amount of time to watch a vod. """
        self.loop_interval_seconds = config.loop_interval_seconds
        """ The amount of seconds in between iterations of the watch loop. """
        self.max_failures_per_streamer = config.max_failures_per_streamer
        """ The maximum number of failed attempt to do per streamer before putting them into a cooldown. """
        self.failure_cooldown_seconds = config.failure_cooldown_seconds
        """ The amount of seconds to wait after failing to make progress `max_attempts_per_streamer` times for a Streamer. """
        self._full_timeout = self.max_seconds_vods + self.max_seconds_clips + 10
        self._failures = dict[str, int]()
        self._cooldowns = dict[str, float]()

    def select_streamers(self):
        """
        Selects Streamers to attempt to progress.
        :return: The Streamers.
        """
        return (
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
            and not self.runner.has_context(streamer)
            # Avoid streamers that are on cooldown
            and streamer.channel_id not in self._cooldowns
        )

    def get_clip(self, streamer: Streamer) -> Clip | None:
        """
        Gets a Clip to Watch for the given Streamer or None if no valid clips can be found.
        :param streamer: The Streamer to check.
        :return: The Clip or None.
        """
        top_clips = streamer.clips.all_time
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
        """
        Gets a VOD for the given Streamer or None if no valid VODs can be found.
        :param streamer: The Streamer to check.
        :return: The VOD or None.
        """
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

    def attempt_progress(self, streamer: Streamer) -> Result:
        clip = self.get_clip(streamer)
        if clip is not None and self.twitch.simulate_clip_playback(
            streamer,
            clip,
            max_watch_seconds=self.max_seconds_clips,
            done=lambda s: not s.missing_weekly_reward(),
        ):
            return Result(success=True, reason="clip")
        if not self.twitch.running:
            return Result(success=False, reason="miner not running")
        vod = self.get_vod(streamer)
        if vod is not None and self.twitch.simulate_vod_playback(
            streamer,
            vod,
            max_watch_seconds=self.max_seconds_vods,
            done=lambda s: not s.missing_weekly_reward(),
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

    def _attempt_progress_lambda(self, streamer: Streamer):
        return lambda: self.attempt_progress(streamer)

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
        Processes a result of a watch attempt.
        :param streamer: The Streamer we attempted to watch.
        :param result: The result to process.
        """
        if result["success"]:
            logger.debug(
                f"Weekly Reward obtained for {streamer} via {result["reason"]}"
            )
            self._failures.pop(streamer.channel_id, None)
            self._cooldowns.pop(streamer.channel_id, None)
        else:
            self.update_failures(streamer.channel_id)
            logger.error(
                f"Unable to progress Weekly Reward for {streamer} with Clips or VODs: {result["reason"]}",
            )

    def manage_cooldowns(self):
        """Checks the cooldowns list and removes items that have been on cooldown long enough."""
        for streamer_id in list(self._cooldowns.keys()):
            start_time = self._cooldowns[streamer_id]
            if (time.monotonic() - start_time) > self.failure_cooldown_seconds:
                self._cooldowns.pop(streamer_id)

    def submit_streamers(self):
        """Finds valid streamers and submits them to be watched."""
        streamers = self.select_streamers()
        while self.runner.has_free_slot():
            streamer = next(streamers, None)
            if streamer is not None:
                logger.debug(f"Beginning progression task for {streamer}")
            if streamer is None or not self.runner.start_task(
                streamer,
                self._attempt_progress_lambda(streamer),
                self._full_timeout,
                on_complete=self.process_result,
            ):
                break

    def _run(self):
        self.manage_cooldowns()
        self.submit_streamers()

    def run(self):
        while self.twitch.running:
            self._run()
            interruptible_sleep(
                running_flag=lambda: self.twitch.running,
                duration=self.loop_interval_seconds,
            )


class WeeklyRewardsProgressorFactory(abc.ABC):
    """Factory that produces WeeklyRewardProgressors."""

    @abc.abstractmethod
    def create(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
    ) -> WeeklyRewardsProgressor:
        pass


class BasicWeeklyRewardsProgressorFactory(WeeklyRewardsProgressorFactory):
    def __init__(
        self,
        runner_factory: SlottedTaskRunnerFactory,
        config: BasicConfiguration | None = None,
    ):
        self.runner_factory = runner_factory
        self.config = config

    def create(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
    ):
        runner = self.runner_factory.create(twitch, "Weekly Rewards Progressor")
        return BasicWeeklyRewardsProgressor(
            twitch, streamers, runner, config=self.config
        )
