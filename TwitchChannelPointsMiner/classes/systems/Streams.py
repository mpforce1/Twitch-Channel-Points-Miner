import logging
import time

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
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

logger = logging.getLogger(__name__)


class StreamSystem:
    def __init__(
        self,
        twitch: Twitch,
        campaigns: dict[str, Campaign],
        streamers: list[Streamer],
        event_manager: EventManager,
    ):
        self.twitch = twitch
        self.streamers = streamers
        self.campaigns = campaigns
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
        # Ignore streamers where claim_drops is NONE
        if streamer.is_online and streamer.settings.claim_drops != DropsMode.NONE:
            # Get campaign data
            new_campaigns = {
                campaign.id: campaign for campaign in self._fetch_progress(streamer)
            }
            # Log the difference
            for old_campaign_id in streamer.stream.campaigns:
                if old_campaign_id not in new_campaigns:
                    old_campaign = self.campaigns.get(old_campaign_id, None)
                    if old_campaign is None:
                        # If we haven't synced the inventory yet, don't worry about logging this
                        continue
                    logger.debug(
                        f"Streamer {streamer} has deactivated Drops Campaign: {old_campaign.name}"
                    )
            for new_campaign_id in new_campaigns:
                if new_campaign_id not in streamer.stream.campaigns:
                    new_campaign = new_campaigns[new_campaign_id]
                    logger.debug(
                        f"Streamer {streamer} has activated Drops Campaign: {new_campaign.name}"
                    )

            # Set the data
            streamer.stream.campaigns = list(new_campaigns.keys())

            # Add any new data to the inventory (the inventory won't have campaigns that haven't been started by the user)
            for campaign_id in new_campaigns:
                if campaign_id not in self.campaigns:
                    campaign = new_campaigns[campaign_id]
                    # Ignore track and lane drops for now
                    can_convert = True
                    for group in campaign.reward_groups:
                        if group.track is not None or group.lane is not None:
                            can_convert = False
                            break
                    if can_convert:
                        self.campaigns[campaign_id] = Campaign.from_gql_stream(campaign)
                        logger.debug(
                            f"Adding new Campaign: {self.campaigns[campaign.id].name}, progressable: {self.campaigns[campaign.id].progressable(True)}"
                        )
                    else:
                        logger.debug(f"Campaign {campaign.name} is invalid")
        else:
            # Clear campaign ids when offline
            streamer.stream.campaigns.clear()
