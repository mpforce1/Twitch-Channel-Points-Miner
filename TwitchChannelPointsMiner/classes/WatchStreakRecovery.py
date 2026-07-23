import abc
import logging
from itertools import chain

from TwitchChannelPointsMiner.classes.ClipVodWatcher import (
    BasicClipVodWatcher,
    BasicConfiguration,
    ClipVodWatcher,
    Result,
)
from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunnerFactory,
)
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer

logger = logging.getLogger(__name__)


class WatchStreakRecovery(ClipVodWatcher, abc.ABC):
    """Attempts to recover missed Watch Streaks by watching Clips/VODs."""

    pass


class BasicWatchStreakRecovery(WatchStreakRecovery, BasicClipVodWatcher):
    def can_watch(self, streamer: Streamer):
        return streamer.needs_watch_streak_recovery()

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

    def process_result(self, streamer: Streamer, result: Result):
        super().process_result(streamer, result)
        if result["success"]:
            logger.debug(
                f"Watch Streak Recovered for {streamer} via {result["reason"]}"
            )
        else:
            logger.error(
                f"Unable to recover Watch Streak for {streamer}: {result["reason"]}"
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
