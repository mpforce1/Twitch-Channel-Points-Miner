import logging

from dateutil import parser as dateparser

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Message import Message
from TwitchChannelPointsMiner.classes.entities.Raid import Raid
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.websocket.MessageListener import MessageListener
from TwitchChannelPointsMiner.classes.websocket.data import OnsiteNotification
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
            streamer = next(
                (
                    streamer
                    for streamer in self.streamers
                    if streamer.channel_id == message.channel_id
                ),
                None,
            )
            if streamer is None and not message.topic in {
                "onsite-notifications",
                "user-subscribe-events-v1",
                "weekly-rewards",
                "viewer-milestones",
            }:
                # these topics aren't channel specific
                return
            if message.topic == "community-points-user-v1":
                if message.type == "points-earned":
                    self.streamer_system.points_earned(
                        channel_id=message.channel_id,
                        timestamp=dateparser.parse(message.timestamp),
                        reason=message.data["point_gain"]["reason_code"],
                        amount=message.data["point_gain"]["total_points"],
                        balance=message.data["balance"]["balance"],
                    )
                elif message.type == "claim-available":
                    self.streamer_system.claim_available(
                        channel_id=message.channel_id,
                        timestamp=dateparser.parse(message.timestamp),
                        claim_id=message.data["claim"]["id"],
                    )
                elif message.type == "points-spent":
                    self.streamer_system.points_spent(
                        channel_id=message.channel_id,
                        timestamp=dateparser.parse(message.timestamp),
                        balance=message.data["balance"]["balance"],
                    )

            elif message.topic == "video-playback-by-id":
                # There is stream-up message type, but it's sent earlier than the API updates
                if message.type == "stream-up":
                    self.stream_system.bring_up(message.channel_id)
                elif message.type == "stream-down":
                    self.stream_system.bring_down(message.channel_id)
                elif message.type == "viewcount":
                    self.stream_system.update_view_count(
                        message.channel_id, message.data["viewcount"]
                    )

            elif message.topic == "raid":
                if message.type == "raid_update_v2":
                    self.streamer_system.raid_update(
                        message.channel_id, raid=Raid(
                            message.message["raid"]["id"],
                            message.message["raid"]["target_login"],
                        )
                    )

            elif message.topic == "community-moments-channel-v1":
                if message.type == "active":
                    self.streamer_system.moment(
                        message.channel_id, message.data["moment_id"]
                    )

            elif message.topic == "predictions-channel-v1":
                event_dict = message.data["event"]
                event_id = event_dict["id"]

                current_tmsp = dateparser.parse(message.timestamp)

                if (
                    message.type == "event-created"
                    and event_id not in self.events_predictions
                ):
                    self.prediction_system.event_created(
                        timestamp=current_tmsp,
                        channel_id=message.channel_id,
                        event_dict=event_dict
                    )
                elif (
                    message.type == "event-updated"
                    and event_id in self.events_predictions
                ):
                    self.prediction_system.event_updated(
                        timestamp=current_tmsp,
                        channel_id=message.channel_id,
                        event_dict=event_dict
                    )

            elif message.topic == "predictions-user-v1":
                event_id = message.data["prediction"]["event_id"]
                if event_id in self.events_predictions:
                    event_prediction = self.events_predictions[event_id]
                    if (
                        message.type == "prediction-result"
                        and event_prediction.bet_confirmed
                    ):
                        self.prediction_system.prediction_result(
                            timestamp=dateparser.parse(message.timestamp),
                            channel_id=message.channel_id,
                            result_dict=message.data["prediction"]
                        )
                    elif message.type == "prediction-made":
                        self.prediction_system.user_prediction_made(
                            channel_id=message.channel_id,
                            event_dict=message.data["prediction"]
                        )
            elif message.topic == "community-points-channel-v1":
                if message.type == "community-goal-created":
                    self.streamer_system.community_goal_created(
                        message.channel_id, message.data["community_goal"]
                    )
                elif message.type == "community-goal-updated":
                    self.streamer_system.community_goal_updated(
                        message.channel_id, message.data["community_goal"]
                    )
                elif message.type == "community-goal-deleted":
                    self.streamer_system.community_goal_deleted(
                        message.channel_id, message.data["community_goal"]
                    )
            elif message.topic == "onsite-notifications":
                logger.debug(f"Received onsite-notification: {message.type}")
                notification = self.parser.parse_onsite_notification(message.message)
                if notification is not None:
                    if isinstance(notification, OnsiteNotification.CreateNotification):
                        if isinstance(
                            notification,
                            OnsiteNotification.UserDropRewardReminderNotification,
                        ):
                            self.notification_system.user_drop_reminder(notification)
                        elif isinstance(
                            notification,
                            OnsiteNotification.UserEarnedQuestsRewardBadgeNotification,
                        ):
                            self.notification_system.user_earned_quests_reward_badge(notification)
                        else:
                            logger.error(
                                f"Unhandled CreateNotification subtype: {type(notification).__name__}"
                            )
                    else:
                        logger.error(
                            f"Unhandled OnsiteNotification subtype: {type(notification).__name__}"
                        )

            elif message.topic == "user-subscribe-events-v1":
                logger.debug(f"Received user-subscribe-events-v1")
                notification = self.parser.parse_user_subscribe_events(message.message)
                self.streamer_system.subscription(notification)

            elif message.topic == "weekly-rewards":
                logger.debug(f"Received weekly-rewards")
                notification = self.parser.parse_weekly_rewards(message.message)
                self.streamer_system.weekly_reward_update(notification)
            elif message.topic == "viewer-milestones":
                logger.debug("Received viewer-milestones")
                viewer_milestones = self.parser.parse_viewer_milestones(message.message)
                if viewer_milestones is not None:
                    self.streamer_system.watch_streak_recovered(viewer_milestones)

        except Exception:
            message_loggable = (
                "REDACTED" if Settings.logger.anonymiser.strict else message
            )
            logger.error(
                f"Exception raised for topic: {message.topic} and message: {message_loggable}",
                exc_info=True,
            )
