import datetime
import logging

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import (
    DropClaim,
    Error,
    DropProgress as DropProgressEvent,
)
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.gql.Errors import RetryError
from TwitchChannelPointsMiner.classes.websocket.data.UserDropEvents import DropProgress
from TwitchChannelPointsMiner.utils.Entities import find_streamer

logger = logging.getLogger(__name__)


class DropsSystem:
    def __init__(
        self,
        campaigns: dict[str, Campaign],
        streamers: list[Streamer],
        twitch: Twitch,
        event_manager: EventManager,
    ):
        self.streamers = streamers
        self.twitch = twitch
        self.event_manager = event_manager
        self.campaigns = campaigns
        self.inventory_updated = datetime.datetime.min
        self.inventory_update_threshold = datetime.timedelta(minutes=15)

    def _refresh_inventory(self):
        if (
            datetime.datetime.now() - self.inventory_updated
        ) > self.inventory_update_threshold:
            try:
                inventory = self.twitch.gql.get_inventory()
                campaign_ids = set()
                # Add/update items
                if inventory.campaigns is not None:
                    for campaign in inventory.campaigns:
                        campaign_ids.add(campaign.id)
                        old_campaign = self.campaigns.get(campaign.id, None)
                        if old_campaign is None:
                            # Add new
                            self.campaigns[campaign.id] = Campaign.from_gql_inventory(
                                campaign
                            )
                            logger.debug(
                                f"Adding new Campaign: {self.campaigns[campaign.id].name}, progressable: {self.campaigns[campaign.id].progressable(True)}"
                            )
                        else:
                            # Update old
                            old_campaign.update(campaign)
                            logger.debug(
                                f"Updating old Campaign: {old_campaign.name}, progressable: {old_campaign.progressable(True)}"
                            )
                # Remove any old campaigns that have been removed from the inventory
                # new campaigns that come from stream data may not yet have shown up
                for campaign_id in list(self.campaigns.keys()):
                    campaign = self.campaigns[campaign_id]
                    if (
                        campaign_id not in campaign_ids
                        and campaign.end_at
                        < datetime.datetime.now(datetime.timezone.utc)
                    ):
                        logger.debug(f"Removing old Campaign: {campaign.name}")
                        self.campaigns.pop(campaign_id)

                self.inventory_updated = datetime.datetime.now()
            except RetryError as e:
                logger.error(f"Error syncing Inventory: {e}")
                self.event_manager.manage(
                    Error(
                        context="Drops System",
                        message="Error syncing Inventory",
                        error=e,
                    )
                )

    def _find_streamer(self, channel_id: str) -> Streamer | None:
        try:
            return find_streamer(self.streamers, channel_id)
        except KeyError:
            return None

    def claim_drop(self, drop: Drop):
        """
        Claims the given Drop.
        :param drop: The Drop to claim.
        :return: True if the Drop could be claimed, False otherwise.
        """
        if drop.drop_instance_id is None:
            logger.debug(f"Unable to claim drop '{drop.id}', no instance id'")
            self.event_manager.manage(
                Error(
                    context="Drops System",
                    message=f"Unable to claim drop '{drop.id}', no instance id'",
                    error=None,
                )
            )
            return False
        logger.info(
            f"Claim {drop}",
            extra={"emoji": ":package:", "event": Events.DROP_CLAIM},
        )
        self.event_manager.manage(
            DropClaim(
                streamer=None,
                drop=drop,
            )
        )
        try:
            response = self.twitch.gql.claim_drop_rewards(drop.drop_instance_id)
        except RetryError as e:
            logger.error(f"Error when claiming drop '{drop.name}': {e}")
            self.event_manager.manage(
                Error(
                    context="Drops System",
                    message="Error when claiming drop",
                    error=e,
                )
            )
            return False
        if response.status is None:
            return False
        if response.error is not None:
            logger.error(
                f"Error while trying to claim drop with id '{drop.drop_instance_id}': {response.error}"
            )
            self.event_manager.manage(
                Error(
                    context="Drops System",
                    message=f"Error while trying to claim drop with id '{drop.drop_instance_id}': {response.error}",
                    error=None,
                )
            )
            return False
        if response.status in [
            "ELIGIBLE_FOR_ALL",
            "DROP_INSTANCE_ALREADY_CLAIMED",
        ]:
            return True
        return False

    def claim_all_drops(self):
        """
        Claims all unclaimed drops from the user's Inventory.
        """
        self._refresh_inventory()
        for campaign in self.campaigns.values():
            if campaign.is_account_connected:
                for drop in campaign.drops.values():
                    if not drop.is_claimed and drop.drop_instance_id is not None:
                        if self.claim_drop(drop):
                            drop.is_claimed = True

    def drop_progress(self, progress: DropProgress):
        streamer = self._find_streamer(progress.channel_id)
        if streamer is None:
            logger.debug(
                f"Drop progress for {progress.drop_id} for untracked Streamer: {progress.channel_id}"
            )
            return
        self._refresh_inventory()
        campaign = next(
            (
                campaign
                for campaign in self.campaigns.values()
                if progress.drop_id in campaign.drops
            ),
            None,
        )
        if campaign is not None:
            drop = campaign.drops[progress.drop_id]
            # Update drop data
            drop.update_progress(progress)

            if Settings.logger.drops_progress:
                completed = sum(
                    1 for drop in campaign.drops.values() if drop.completed()
                )
                groups = sum(
                    1
                    for drop in campaign.drops.values()
                    if drop.meets_base_requirements()
                )
                name_resolved = drop.name.strip()
                if name_resolved is None or name_resolved == "":
                    name_resolved = campaign.name.strip()
                game_resolved = (
                    campaign.game.display_name
                    if campaign.game is not None
                    else "General"
                )
                # Format:
                # |█████     |    {percent progress}% [{watched}/{required}]: {streamer}: {category}: {name}: {count}/{total}
                logger.info(
                    f"{drop.progress_bar()}: "
                    f"{streamer.username}: "
                    f"{game_resolved}: "
                    f"{name_resolved}: "
                    # If this drop has just completed, we still want the update to refer to it with the same number/total
                    f"{completed + (0 if drop.completed() else 1)}/{groups}",
                    extra={"event": Events.DROP_STATUS},
                )

            self.event_manager.manage(
                DropProgressEvent(
                    streamer=streamer,
                    drop=drop,
                    progress=progress.current_progress,
                )
            )
        else:
            logger.debug(f"Progress for untracked drop: {progress.drop_id}")
