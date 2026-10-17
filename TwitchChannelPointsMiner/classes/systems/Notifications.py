import logging

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import DropClaimAvailable
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.systems.Drops import DropsSystem
from TwitchChannelPointsMiner.classes.websocket.data import OnsiteNotification

logger = logging.getLogger(__name__)


class NotificationsSystem:
    def __init__(
        self, streamers: list[Streamer], drops_system: DropsSystem, event_manager: EventManager
    ):
        self.streamers = streamers
        self.drops_system = drops_system
        self.event_manager = event_manager

    def user_drop_reminder(
        self, notification: OnsiteNotification.UserDropRewardReminderNotification
    ):
        logger.info(
            f"Drop claimable: {notification.drop_name}",
            extra={"emoji": ":package:", "event": Events.DROP_CLAIM_AVAILABLE},
        )
        self.event_manager.manage(
            DropClaimAvailable(
                streamer=None,
                drop=notification.drop_name
            )
        )
        self.drops_system.claim_all_drops()

    def user_earned_quests_reward_badge(
        self, notification: OnsiteNotification.UserEarnedQuestsRewardBadgeNotification
    ):
        logger.debug(f"Badge Earned: {notification.badge_name}")
