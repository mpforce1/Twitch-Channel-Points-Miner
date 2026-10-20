import logging
import time

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import DropsMode, Streamer
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
)
from TwitchChannelPointsMiner.utils.Entities import find_streamer
from TwitchChannelPointsMiner.utils.Utils import oxford_comma_list

logger = logging.getLogger(__name__)


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
        if streamer.is_online and streamer.settings.claim_drops in {
            DropsMode.ALL,
            DropsMode.LINKED,
        }:
            # Get campaign data
            new_campaigns = {
                campaign.id: campaign for campaign in self._fetch_progress(streamer)
            }
            # Log the difference
            for old_campaign_id in streamer.stream.campaigns:
                if old_campaign_id not in new_campaigns:
                    old_campaign = streamer.stream.campaigns[old_campaign_id]
                    logger.info(
                        f"Streamer {streamer} has deactivated Drops Campaign: {old_campaign.name}"
                    )
            for new_campaign_id in new_campaigns:
                if new_campaign_id not in streamer.stream.campaigns:
                    new_campaign = new_campaigns[new_campaign_id]
                    logger.info(
                        f"Streamer {streamer} has activated Drops Campaign: {new_campaign.name}. "
                        f"Available drops: {oxford_comma_list([reward.name for group in new_campaign.reward_groups for reward in group.rewards])}"
                    )

            # Set the data
            streamer.stream.campaigns = new_campaigns
        else:
            # Clear campaign ids when offline
            streamer.stream.campaigns.clear()
