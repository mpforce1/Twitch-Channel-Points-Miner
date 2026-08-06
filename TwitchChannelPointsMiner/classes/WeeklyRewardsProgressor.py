import abc
import logging
from threading import Thread
from typing import Literal, TypedDict

from TwitchChannelPointsMiner.classes.ClipVodWatcher import (
    BasicClipVodWatcher,
    BasicConfiguration,
    ClipVodWatcher,
)
from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunnerFactory,
)
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.Video import Video
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip

logger = logging.getLogger(__name__)


class Result(TypedDict):
    success: bool
    reason: str


class WeeklyRewardsProgressor(ClipVodWatcher, abc.ABC):
    """Attempts to progress Weekly Rewards by watching Clips and VODs."""

    pass


class BasicWeeklyRewardsProgressor(WeeklyRewardsProgressor, BasicClipVodWatcher):
    def can_watch(self, streamer: Streamer) -> bool:
        """
        Selects Streamers to attempt to progress.
        :return: The Streamers.
        """
        return not streamer.is_online and streamer.missing_weekly_reward()

    def done_watching(self, streamer: Streamer) -> bool:
        # Override base class behaviour to continue watching if a Streamer comes online.
        return not streamer.missing_weekly_reward()

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

    def get_vod(self, streamer: Streamer) -> Video | None:
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
                return video
        logger.debug(f"All {len(recent_broadcasts)} recent VODs too short")
        return None

    def process_result(self, streamer: Streamer, result: Result):
        super().process_result(streamer, result)
        if result["success"]:
            logger.debug(
                f"Weekly Reward obtained for {streamer} via {result["reason"]}"
            )
        else:
            logger.error(
                f"Unable to progress Weekly Reward for {streamer} with Clips or VODs: {result["reason"]}",
            )


class WeeklyRewardsProgressorFactory(abc.ABC):
    """Factory that produces WeeklyRewardProgressors."""

    @abc.abstractmethod
    def create(
        self,
        config: BasicConfiguration | Literal[False] | None,
        twitch: Twitch,
        streamers: list[Streamer],
        background_tasks: list[Thread],
        event_manager: EventManager,
    ) -> WeeklyRewardsProgressor | None:
        pass


class BasicWeeklyRewardsProgressorFactory(WeeklyRewardsProgressorFactory):
    def __init__(
        self,
        runner_factory: SlottedTaskRunnerFactory,
    ):
        self.runner_factory = runner_factory

    def create(
        self,
        config: BasicConfiguration | Literal[False] | None,
        twitch: Twitch,
        streamers: list[Streamer],
        background_tasks: list[Thread],
        event_manager: EventManager,
    ):
        if config is False:
            return None
        elif config is None:
            config = BasicConfiguration()
        runner = self.runner_factory.create(
            name="Weekly Rewards Progressor", event_manager=event_manager
        )
        progressor = BasicWeeklyRewardsProgressor(
            twitch, streamers, runner, event_manager=event_manager, config=config
        )
        progressor.start()
        background_tasks.append(progressor)
        return progressor
