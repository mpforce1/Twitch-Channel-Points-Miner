import logging

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.websocket.data import OnsiteNotification

logger = logging.getLogger(__name__)


class NotificationsSystem:
    def __init__(
        self, twitch: Twitch, streamers: list[Streamer], event_manager: EventManager
    ):
        self.twitch = twitch
        self.streamers = streamers
        self.event_manager = event_manager

    def user_drop_reminder(
        self, notification: OnsiteNotification.UserDropRewardReminderNotification
    ):
        logger.info(f"Drop claimable: {notification.drop_name}")
        self.twitch.claim_all_drops_from_inventory()

    def user_earned_quests_reward_badge(
        self, notification: OnsiteNotification.UserEarnedQuestsRewardBadgeNotification
    ):
        logger.debug(f"Badge Earned: {notification.badge_name}")
