import logging

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Message import Message
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.websocket.MessageListener import MessageListener
from TwitchChannelPointsMiner.classes.websocket.data import (
    CommunityMomentsChannel,
    CommunityPointsChannel,
    CommunityPointsUser,
    OnsiteNotification,
    PredictionsChannel,
    PredictionsUser,
    Raid,
    UserSubscribeEvents,
    VideoPlaybackById,
    ViewerMilestones,
    WeeklyRewards,
)
from TwitchChannelPointsMiner.classes.websocket.data.Parser import Parser
from TwitchChannelPointsMiner.systems.Notifications import NotificationsSystem
from TwitchChannelPointsMiner.systems.Predictions import PredictionSystem
from TwitchChannelPointsMiner.systems.Streamers import StreamerSystem
from TwitchChannelPointsMiner.systems.Streams import StreamSystem

logger = logging.getLogger(__name__)


class PubSubHandler(MessageListener):
    """
    Listener for PubSub format Messages that handles them in a client agnostic way, i.e. this works with messages from
    both the legacy PubSub and Hermes WebSocket APIs.
    """

    def __init__(
        self,
        streamer_system: StreamerSystem,
        stream_system: StreamSystem,
        prediction_system: PredictionSystem,
        notification_system: NotificationsSystem,
        parser: Parser,
        twitch: Twitch,
        streamers: list[Streamer],
        events_predictions: dict,
    ):
        self.streamer_system = streamer_system
        self.stream_system = stream_system
        self.prediction_system = prediction_system
        self.notification_system = notification_system
        self.parser = parser
        self.twitch = twitch
        self.streamers = streamers
        self.events_predictions = events_predictions

    def on_message(self, message: Message):
        try:
            data = self.parser.message_parser(message.data, message.topic)
            # Dispatch data by type to the relevant system method
            match data:
                case CommunityPointsUser.PointsEarned():
                    self.streamer_system.points_earned(data)
                case CommunityPointsUser.PointsSpent():
                    self.streamer_system.points_spent(data)
                case CommunityPointsUser.ClaimAvailable():
                    self.streamer_system.claim_available(data)
                case VideoPlaybackById.StreamUp():
                    self.stream_system.bring_up(message.channel_id)
                case VideoPlaybackById.StreamDown():
                    self.stream_system.bring_down(message.channel_id)
                case VideoPlaybackById.ViewCount():
                    self.stream_system.update_view_count(
                        message.channel_id, data.viewers
                    )
                case Raid.RaidUpdate():
                    self.streamer_system.raid_update(message.channel_id, data)
                case CommunityMomentsChannel.Active():
                    self.streamer_system.moment(message.channel_id, data.id)
                case PredictionsChannel.EventCreated():
                    self.prediction_system.event_created(data)
                case PredictionsChannel.EventUpdated():
                    self.prediction_system.event_updated(data)
                case PredictionsUser.PredictionMade():
                    self.prediction_system.user_prediction_made(data)
                case PredictionsUser.PredictionResult():
                    self.prediction_system.prediction_result(data)
                case CommunityPointsChannel.CommunityGoalCreated():
                    self.streamer_system.community_goal_created(
                        message.channel_id, data
                    )
                case CommunityPointsChannel.CommunityGoalUpdated():
                    self.streamer_system.community_goal_updated(
                        message.channel_id, data
                    )
                case CommunityPointsChannel.CommunityGoalDeleted():
                    self.streamer_system.community_goal_deleted(
                        message.channel_id, data
                    )
                case OnsiteNotification.UserDropRewardReminderNotification():
                    self.notification_system.user_drop_reminder(data)
                case OnsiteNotification.UserEarnedQuestsRewardBadgeNotification():
                    self.notification_system.user_earned_quests_reward_badge(data)
                case UserSubscribeEvents.UserSubscribed():
                    self.streamer_system.subscription(data)
                case WeeklyRewards.Notification():
                    self.streamer_system.weekly_reward_update(data)
                case ViewerMilestones.StreakRecovered():
                    self.streamer_system.watch_streak_recovered(data)
                case _:
                    raise ValueError(f"Unhandled WebSocket Message: {data}")
        except Exception:
            message_loggable = (
                "REDACTED" if Settings.logger.anonymiser.strict else message
            )
            logger.error(
                f"Exception raised for topic: {message.topic} and message: {message_loggable}",
                exc_info=True,
            )
