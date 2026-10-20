import datetime
import logging
import math

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.Twitch import Twitch
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
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import InventoryResponse
from TwitchChannelPointsMiner.classes.websocket.data.UserDropEvents import DropProgress
from TwitchChannelPointsMiner.utils.Entities import find_streamer

logger = logging.getLogger(__name__)


class DropsSystem:
    def __init__(
        self, streamers: list[Streamer], twitch: Twitch, event_manager: EventManager
    ):
        self.streamers = streamers
        self.twitch = twitch
        self.event_manager = event_manager
        self.inventory = None
        self.inventory_updated = datetime.datetime.min
        self.inventory_update_threshold = datetime.timedelta(minutes=15)

    def _refresh_inventory(self) -> InventoryResponse | None:
        if (
            datetime.datetime.now() - self.inventory_updated
        ) > self.inventory_update_threshold:
            try:
                self.inventory = self.twitch.gql.get_inventory()
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
                return None

        return self.inventory

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
        inventory = self._refresh_inventory()
        if inventory is not None and inventory.campaigns is not None:
            for campaign in inventory.campaigns:
                if campaign.is_account_connected:
                    for drop in campaign.time_based_drops:
                        if (
                            not drop.self_edge.is_claimed
                            and drop.self_edge.drop_instance_id is not None
                        ):
                            if self.claim_drop(Drop.from_gql(drop)):
                                drop.self_edge.is_claimed = True

    def _progress_bar(self, current: int, required: int, segments=10):
        percentage_progress = current / required if required != 0 else 0
        progress = math.floor(percentage_progress * segments)
        remaining = segments - progress
        return f"|{('█' * progress)}{(' ' * remaining)}|\t{percentage_progress * 100:.2f}% [{current}/{required}]"

    def drop_progress(self, progress: DropProgress):
        streamer = self._find_streamer(progress.channel_id)
        if streamer is None:
            logger.debug(
                f"Drop progress for {progress.drop_id} for untracked Streamer: {progress.channel_id}"
            )
            return
        inventory = self._refresh_inventory()
        if inventory is not None and inventory.campaigns is not None:
            campaign_and_drop = next(
                (
                    (campaign, drop)
                    for campaign in inventory.campaigns
                    for drop in campaign.time_based_drops
                    if drop.id == progress.drop_id
                ),
                None,
            )
            if campaign_and_drop is not None:
                campaign, drop = campaign_and_drop
                # Update drop data
                drop.self_edge.current_minutes_watched = progress.current_progress_min

                if Settings.logger.drops_progress:
                    logger.info(
                        f"{self._progress_bar(progress.current_progress_min, progress.required_progress_min)}: "
                        f"{streamer}: {campaign.name}: {drop.name}",
                        extra={"event": Events.DROP_STATUS},
                    )

                self.event_manager.manage(
                    DropProgressEvent(
                        streamer=streamer,
                        drop=Drop.from_gql(drop),
                        progress=progress.current_progress,
                    )
                )
            else:
                logger.debug(f"Progress for untracked drop: {progress.drop_id}")
