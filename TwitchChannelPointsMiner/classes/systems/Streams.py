import datetime
import logging
import time

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import (
    Error,
    StreamDown,
    StreamUp,
    StreamViewCount,
    StreamerOffline,
)
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.gql.Errors import RetryError
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropsCampaign,
    DropsRewardGroup,
)
from TwitchChannelPointsMiner.utils.Entities import find_streamer
from TwitchChannelPointsMiner.utils.Utils import oxford_comma_list

logger = logging.getLogger(__name__)


def is_reward_group_progressable(group: DropsRewardGroup) -> bool:
    group.rewards = [reward for reward in group.rewards if reward.is_account_connected]
    requirements = group.progress_criteria.requirements
    # Filter groups with no rewards
    if len(group.rewards) <= 0:
        return False
    # Filter groups with a turbo sub requirement
    if requirements.turbo_subs > 0:
        return False
    if group.self_edge is None:
        current_subs = 0
        current_minutes_watched = 0
        status = None
    else:
        current_subs = group.self_edge.current_subs
        current_minutes_watched = group.self_edge.current_minutes_watched
        status = group.self_edge.status
    # Filter groups with a higher sub requirement than the user has
    if requirements.subs > current_subs:
        return False
    # Filter groups with more minutes watched than required
    if current_minutes_watched >= requirements.minutes_watched:
        return False
    # Filter groups that are already claimable/claimed
    if status in {"CLAIMABLE", "CLAIMED"}:
        return False
    return True


def is_campaign_progressable(campaign: DropsCampaign) -> bool:
    if campaign.end_at < datetime.datetime.now(datetime.timezone.utc):
        return False
    campaign.reward_groups = [
        group for group in campaign.reward_groups if is_reward_group_progressable(group)
    ]
    if len(campaign.reward_groups) == 0:
        return False
    return True


class StreamSystem:
    def __init__(
        self, twitch: Twitch, streamers: list[Streamer], event_manager: EventManager
    ):
        self.twitch = twitch
        self.streamers = streamers
        self.event_manager = event_manager

    def bring_up(self, channel_id: str):
        """
        Sets the Stream of the Streamer with the given id to up.
        :param channel_id: The id of the Streamer
        """
        streamer = find_streamer(self.streamers, channel_id)
        streamer.stream_up = time.time()
        self.event_manager.manage(StreamUp(streamer=streamer))
        # No StreamerOnline as it can take a few seconds for the stream URL to become available

    def bring_down(self, channel_id: str):
        """
        Sets the Stream of the Streamer with the given id to down.
        :param channel_id: The id of the Streamer.
        """
        streamer = find_streamer(self.streamers, channel_id)
        if streamer.is_online:
            streamer.set_offline()
            self.event_manager.manage(StreamDown(streamer=streamer))
            self.event_manager.manage(StreamerOffline(streamer=streamer))

    def update_view_count(self, channel_id: str, view_count: int):
        """
        Updates the view count of the Stream of the Streamer with the given id.
        :param channel_id: The id of the Streamer.
        :param view_count: The current view count.
        """
        streamer = find_streamer(self.streamers, channel_id)
        if streamer.stream_up_elapsed():
            self.twitch.check_streamer_online(streamer)
        self.event_manager.manage(
            StreamViewCount(streamer=streamer, view_count=view_count)
        )

    def _fetch_progress(self, streamer: Streamer) -> list[DropsCampaign]:
        # Fetch new data
        try:
            campaigns = self.twitch.gql.drop_channel_campaigns_progress(
                streamer.channel_id
            )
        except RetryError as e:
            logger.error(
                f"Exception getting Drop Campaigns Progress for {streamer}: {e}"
            )
            self.event_manager.manage(
                Error(
                    context="Drop Campaign Updater",
                    message=f"Exception getting Drop Campaigns for {streamer}",
                    error=e,
                )
            )
            return []

        if campaigns.campaigns is None:
            return []
        return campaigns.campaigns

    def update_campaigns(self, channel_id: str):
        """
        Updates the list of campaign ids for the Stream of the given Streamer.
        :param channel_id: The id of the Streamer
        """
        streamer = find_streamer(self.streamers, channel_id)
        if streamer.is_online and streamer.settings.claim_drops is True:
            # Get campaign data
            in_progress_campaigns = self._fetch_progress(streamer)
            # Filter out unprogressable campaigns and extract ids
            streamer.stream.campaigns_ids = [
                campaign.id
                for campaign in in_progress_campaigns
                if is_campaign_progressable(campaign)
            ]
            logger.info(
                f"{streamer} Campaigns: {oxford_comma_list(streamer.stream.campaigns_ids)}"
            )
        else:
            # Clear campaign ids when offline
            streamer.stream.campaigns_ids = []
