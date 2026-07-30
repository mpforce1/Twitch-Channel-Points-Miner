import logging
from typing import Callable, Literal

from TwitchChannelPointsMiner.JsonParser import (
    InvalidJsonShapeError,
    JsonParentContext,
    expect_bool,
    expect_dict,
    expect_iso_8601,
    expect_server_time,
    expect_str,
    list_parser,
    optional_parser,
    parse_expected_value,
    dig,
    expect_int,
    parse_value,
)
from TwitchChannelPointsMiner.classes.websocket.data import (
    CommunityMomentsChannel,
    CommunityPointsUser,
    Predictions,
    Raid,
    UserSubscribeEvents,
    ViewerMilestones,
    WeeklyRewards,
    VideoPlaybackById,
    PredictionsChannel,
    PredictionsUser,
    CommunityPointsChannel,
    OnsiteNotification,
)
from TwitchChannelPointsMiner.classes.websocket.data.Model import Model
from TwitchChannelPointsMiner.utils import ordinal

logger = logging.getLogger(__name__)


def parse_wrapped_markdown_segment(source: str, wrapper: str, index: int = 0) -> str:
    """
    Parse the segment in the given Markdown string that's wrapped with the given wrapper string. Can be used to get
    things like quoted or bold segments. If an index is supplied then the (index + 1)th wrapped segment will be
    returned. i.e. `index=0` gives you the 1st wrapped segment, `index=1` gives you the 2nd wrapped segment.
    Does not return the wrapper tags (i.e. ** or "), just the contained string.

    :param source: The Markdown string to search.
    :param wrapper: The Markdown wrapper string.
    :param index: The ordered index of the wrapped segment.
    :return: The wrapped segment.
    :raises ValueError: If the segment could not be found.
    """
    wrapper_len = len(wrapper)
    count = 0
    previous_last_bold_marker = -wrapper_len
    while count <= index:
        first_wrapper_index = source.find(
            wrapper, previous_last_bold_marker + wrapper_len
        )
        second_wrapper_index = source.find(wrapper, first_wrapper_index + wrapper_len)
        if first_wrapper_index == -1 or second_wrapper_index == -1:
            raise InvalidJsonShapeError(
                [],
                f"Unable to find {ordinal(count + 1)} wrapper markers ({wrapper}) in source: '{source}'",
            )
        if count == index:
            return source[first_wrapper_index + wrapper_len : second_wrapper_index]
        else:
            count += 1
            previous_last_bold_marker = second_wrapper_index
    raise ValueError(f"Index {index} must be greater than 0.")


class Parser:
    def __init__(self):
        self.community_points_user_parsers = {
            "points-earned": self.community_points_user_points_earned_parser,
            "points-spent": self.community_points_user_points_spent_parser,
            "claim-available": self.community_points_user_claim_available_parser,
        }
        self.video_playback_by_id_parsers = {
            "stream-up": self.video_playback_by_id_stream_up_parser,
            "stream-down": self.video_playback_by_id_stream_down_parser,
            "viewcount": self.video_playback_by_id_viewcount_parser,
        }
        self.raid_parsers = {"raid_update_v2": self.raid_update_parser}
        self.community_moments_channel_parsers = {
            "active": self.community_moments_channel_active_parser
        }
        self.predictions_channel_parsers = {
            "event-created": self.predictions_channel_event_created_parser,
            "event-updated": self.predictions_channel_event_updated_parser,
        }
        self.predictions_user_parsers = {
            "prediction-made": self.predictions_user_prediction_made_parser,
            "prediction-result": self.predictions_user_prediction_result_parser,
        }
        self.community_points_channel_parsers = {
            "community-goal-created": self.community_points_channel_created_parser,
            "community-goal-updated": self.community_points_channel_updated_parser,
            "community-goal-deleted": self.community_points_channel_deleted_parser,
        }

        self.onsite_notification_parsers = {
            "create-notification": self.create_notification_parser
        }
        self.ignorable_onsite_notification_types = ["update-summary"]
        self.create_notification_parsers = {
            "user_drop_reward_reminder_notification": self.user_drop_reward_reminder_notification_parser,
            "quests_viewer_reward_campaign_earned_badge": self.quests_viewer_reward_campaign_earned_badge_parser,
        }
        self.parsers = {
            "community-points-user-v1": self.community_points_user_parser,
            "video-playback-by-id": self.video_playback_by_id_parser,
            "raid": self.raid_parser,
            "community-moments-channel-v1": self.community_moments_channel_parser,
            "predictions-channel-v1": self.predictions_channel_parser,
            "predictions-user-v1": self.predictions_user_parser,
            "community-points-channel-v1": self.community_points_channel_parser,
            "onsite-notifications": self.onsite_notification_parser,
            "user-subscribe-events-v1": self.user_subscribe_events_parser,
            "weekly-rewards": self.weekly_rewards_parser,
            "viewer-milestones": self.viewer_milestones_parser,
        }

    def _sub_type_parser[Result](
        self,
        message,
        sub_types: dict[str, Callable[[object], Result]],
        type_field: str | Literal["type"] = "type",
        data_field: str | Literal["data"] | None = "data",
    ) -> Result | None:
        """
        Parses the "data" field of the given message (or the whole message) using the sub parser mapped to the value of
        the "type" field.
        :param message: An object containing a "type" and "data" field.
        :param sub_types: A dict of sub parser functions.
        :param type_field: The name of the "type" field.
        :param data_field: The name of the "data" field, or None if the whole message should be used.
        """
        message = expect_dict(message)
        _type = parse_expected_value(message, type_field, expect_str)
        sub_parser = sub_types.get(_type, None)
        if sub_parser is not None:
            if data_field is None:
                return sub_parser(message)
            else:
                return parse_expected_value(message, data_field, sub_parser)
        else:
            return None

    # community-points-user-v1
    def community_points_user_points_earned_parser(
        self, data
    ) -> CommunityPointsUser.PointsEarned:
        data = expect_dict(data)
        return CommunityPointsUser.PointsEarned(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            channel_id=parse_expected_value(data, "channel_id", expect_str),
            amount=dig(data, ["point_gain", "total_points"], expect_int),
            balance=dig(data, ["balance", "balance"], expect_int),
            reason=dig(data, ["point_gain", "reason_code"], expect_str),
        )

    def community_points_user_points_spent_parser(
        self, data
    ) -> CommunityPointsUser.PointsSpent:
        data = expect_dict(data)
        return CommunityPointsUser.PointsSpent(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            channel_id=dig(data, ["balance", "channel_id"], expect_str),
            balance=dig(data, ["balance", "balance"], expect_int),
        )

    def community_points_user_claim_available_parser(
        self, data
    ) -> CommunityPointsUser.ClaimAvailable:
        data = expect_dict(data)
        return CommunityPointsUser.ClaimAvailable(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            channel_id=dig(data, ["claim", "channel_id"], expect_str),
            claim_id=dig(data, ["claim", "id"], expect_str),
            amount=dig(data, ["claim", "point_gain", "total_points"], expect_int),
        )

    def community_points_user_parser(self, message) -> CommunityPointsUser.Model | None:
        return self._sub_type_parser(message, self.community_points_user_parsers)

    # video-playback-by-id

    def video_playback_by_id_stream_up_parser(self, message):
        message = expect_dict(message)
        return VideoPlaybackById.StreamUp(
            timestamp=parse_expected_value(message, "server_time", expect_server_time),
        )

    def video_playback_by_id_stream_down_parser(self, message):
        message = expect_dict(message)
        return VideoPlaybackById.StreamDown(
            timestamp=parse_expected_value(message, "server_time", expect_server_time),
        )

    def video_playback_by_id_viewcount_parser(self, message):
        message = expect_dict(message)
        return VideoPlaybackById.ViewCount(
            timestamp=parse_expected_value(message, "server_time", expect_server_time),
            viewers=parse_expected_value(message, "viewers", expect_int),
        )

    def video_playback_by_id_parser(self, message) -> VideoPlaybackById.Model | None:
        return self._sub_type_parser(
            message, self.video_playback_by_id_parsers, data_field=None
        )

    # raid

    def raid_update_parser(self, raid):
        raid = expect_dict(raid)
        return Raid.RaidUpdate(
            id=parse_expected_value(raid, "id", expect_str),
            target_id=parse_expected_value(raid, "target_id", expect_str),
            target_username=parse_expected_value(raid, "target_login", expect_str),
            target_display_name=parse_expected_value(
                raid, "target_display_name", expect_str
            ),
        )

    def raid_parser(self, message) -> Raid.Model | None:
        return self._sub_type_parser(message, self.raid_parsers, data_field="raid")

    # community-moments-channel-v1

    def community_moments_channel_active_parser(self, message):
        message = expect_dict(message)
        return CommunityMomentsChannel.Active(
            id=parse_expected_value(message, "moment_id", expect_str)
        )

    def community_moments_channel_parser(
        self, message
    ) -> CommunityMomentsChannel.Model | None:
        return self._sub_type_parser(
            message, self.community_moments_channel_parsers, data_field=None
        )

    # predictions
    def prediction_user_parser(self, user) -> Predictions.User:
        user = expect_dict(user)
        return Predictions.User(
            id=parse_expected_value(user, "user_id", expect_str),
            display_name=parse_expected_value(user, "user_display_name", expect_str),
        )

    def prediction_result_parser(self, result):
        result = expect_dict(result)
        return Predictions.Result(
            type=parse_expected_value(result, "type", expect_str),
            points_won=parse_expected_value(
                result, "points_won", optional_parser(expect_int)
            ),
        )

    def prediction_prediction_parser(self, prediction):
        prediction = expect_dict(prediction)
        return Predictions.Prediction(
            id=parse_expected_value(prediction, "id", expect_str),
            event_id=parse_expected_value(prediction, "event_id", expect_str),
            outcome_id=parse_expected_value(prediction, "outcome_id", expect_str),
            channel_id=parse_expected_value(prediction, "channel_id", expect_str),
            points=parse_expected_value(prediction, "points", expect_int),
            predicted_at=parse_expected_value(
                prediction, "predicted_at", expect_iso_8601
            ),
            updated_at=parse_expected_value(prediction, "updated_at", expect_iso_8601),
            user_id=parse_expected_value(prediction, "user_id", expect_str),
            result=parse_expected_value(
                prediction, "result", optional_parser(self.prediction_result_parser)
            ),
            user_display_name=parse_expected_value(
                prediction, "user_display_name", optional_parser(expect_str)
            ),
        )

    def prediction_outcome_parser(self, outcome):
        outcome = expect_dict(outcome)
        return Predictions.Outcome(
            id=parse_expected_value(outcome, "id", expect_str),
            color=parse_expected_value(outcome, "color", expect_str),
            title=parse_expected_value(outcome, "title", expect_str),
            total_points=parse_expected_value(outcome, "total_points", expect_int),
            total_users=parse_expected_value(outcome, "total_users", expect_int),
            top_predictors=parse_expected_value(
                outcome,
                "top_predictors",
                list_parser(self.prediction_prediction_parser),
            ),
        )

    def prediction_event_parser(self, event) -> Predictions.PredictionEvent:
        event = expect_dict(event)
        return Predictions.PredictionEvent(
            id=parse_expected_value(event, "id", expect_str),
            channel_id=parse_expected_value(event, "channel_id", expect_str),
            created_at=parse_expected_value(event, "created_at", expect_iso_8601),
            created_by=parse_expected_value(
                event,
                "created_by",
                self.prediction_user_parser,
            ),
            ended_at=parse_expected_value(
                event, "ended_at", optional_parser(expect_iso_8601)
            ),
            ended_by=parse_expected_value(
                event, "ended_by", optional_parser(self.prediction_user_parser)
            ),
            locked_at=parse_expected_value(
                event, "locked_at", optional_parser(expect_iso_8601)
            ),
            locked_by=parse_expected_value(
                event,
                "locked_by",
                optional_parser(self.prediction_user_parser),
            ),
            outcomes=parse_expected_value(
                event, "outcomes", list_parser(self.prediction_outcome_parser)
            ),
            prediction_window_seconds=parse_expected_value(
                event, "prediction_window_seconds", expect_int
            ),
            status=parse_expected_value(event, "status", expect_str),
            title=parse_expected_value(event, "title", expect_str),
            winning_outcome_id=parse_expected_value(
                event, "winning_outcome_id", optional_parser(expect_str)
            ),
        )

    # predictions-channel-v1

    def predictions_channel_event_created_parser(self, data):
        data = expect_dict(data)
        return PredictionsChannel.EventCreated(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            event=parse_expected_value(data, "event", self.prediction_event_parser),
        )

    def predictions_channel_event_updated_parser(self, data):
        data = expect_dict(data)
        return PredictionsChannel.EventUpdated(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            event=parse_expected_value(data, "event", self.prediction_event_parser),
        )

    def predictions_channel_parser(self, message) -> PredictionsChannel.Model | None:
        return self._sub_type_parser(message, self.predictions_channel_parsers)

    # predictions-user-v1
    def predictions_user_prediction_made_parser(self, data):
        data = expect_dict(data)
        return PredictionsUser.PredictionMade(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            prediction=parse_expected_value(
                data, "prediction", self.prediction_prediction_parser
            ),
        )

    def predictions_user_prediction_result_parser(self, data):
        data = expect_dict(data)
        return PredictionsUser.PredictionResult(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            prediction=parse_expected_value(
                data, "prediction", self.prediction_prediction_parser
            ),
        )

    def predictions_user_parser(self, message) -> PredictionsUser.Model | None:
        return self._sub_type_parser(message, self.predictions_user_parsers)

    # community-points-channel-v1
    def community_goal_parser(self, goal):
        goal = expect_dict(goal)
        return CommunityPointsChannel.Goal(
            id=parse_expected_value(goal, "id", expect_str),
            title=parse_expected_value(goal, "title", expect_str),
            is_in_stock=parse_expected_value(goal, "is_in_stock", expect_bool),
            points_contributed=parse_expected_value(
                goal, "points_contributed", expect_int
            ),
            goal_amount=parse_expected_value(goal, "goal_amount", expect_int),
            per_stream_maximum_user_contribution=parse_expected_value(
                goal, "per_stream_maximum_user_contribution", expect_int
            ),
            status=parse_expected_value(goal, "status", expect_str),
        )

    def community_points_channel_created_parser(self, data):
        data = expect_dict(data)
        return CommunityPointsChannel.CommunityGoalCreated(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            goal=parse_expected_value(
                data, "community_goal", self.community_goal_parser
            ),
        )

    def community_points_channel_updated_parser(self, data):
        data = expect_dict(data)
        return CommunityPointsChannel.CommunityGoalUpdated(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            goal=parse_expected_value(
                data, "community_goal", self.community_goal_parser
            ),
        )

    def community_points_channel_deleted_parser(self, data):
        data = expect_dict(data)
        return CommunityPointsChannel.CommunityGoalDeleted(
            timestamp=parse_expected_value(data, "timestamp", expect_iso_8601),
            goal=parse_expected_value(
                data, "community_goal", self.community_goal_parser
            ),
        )

    def community_points_channel_parser(
        self, message
    ) -> CommunityPointsChannel.Model | None:
        return self._sub_type_parser(message, self.community_points_channel_parsers)

    # onsite-notifications

    def user_drop_reward_reminder_notification_parser(
        self, notification
    ) -> OnsiteNotification.UserDropRewardReminderNotification | None:
        notification = expect_dict(notification)
        body = parse_expected_value(notification, "body_md", expect_str)
        with JsonParentContext("body_md"):
            # The drop name is in the first set of bold markdown tags
            try:
                drop_name = parse_wrapped_markdown_segment(body, "**")
            except InvalidJsonShapeError:
                # If the drop name can't be found then the notification can be ignored
                return None

        image_url = dig(
            notification,
            ["data_blocks", 1, "content", "image_block", "url"],
            expect_str,
        )
        return OnsiteNotification.UserDropRewardReminderNotification(
            drop_name=drop_name,
            image_url=image_url,
        )

    def quests_viewer_reward_campaign_earned_badge_parser(self, notification):
        notification = expect_dict(notification)
        body = parse_expected_value(notification, "body_md", expect_str)
        with JsonParentContext("body_md"):
            # The badge name is in the first set of quotes
            badge_name = parse_wrapped_markdown_segment(body, '"')
        image_url = dig(
            notification,
            ["data_blocks", 0, "content", "image_block", "url"],
            expect_str,
        )
        return OnsiteNotification.UserEarnedQuestsRewardBadgeNotification(
            badge_name=badge_name,
            image_url=image_url,
        )

    def create_notification_parser(
        self, data
    ) -> OnsiteNotification.CreateNotification | None:
        data = expect_dict(data)
        notification = parse_expected_value(data, "notification", expect_dict)
        with JsonParentContext("notification"):
            _type = parse_expected_value(notification, "type", expect_str)
            if _type in self.create_notification_parsers:
                return self.create_notification_parsers[_type](notification)
            else:
                logger.debug(f"Unknown create-notification type: {_type}")
                return None

    def onsite_notification_parser(self, value) -> OnsiteNotification.Model | None:
        value = expect_dict(value)
        _type = parse_expected_value(value, "type", expect_str)
        if _type in self.onsite_notification_parsers:
            return parse_expected_value(
                value, "data", self.onsite_notification_parsers[_type]
            )
        else:
            if _type not in self.ignorable_onsite_notification_types:
                logger.debug(f"Unknown onsite-notification type: {_type}")
            return None

    # user-subscribe-events-v1

    def user_subscribe_events_parser(self, value) -> UserSubscribeEvents.Model:
        value = expect_dict(value)
        return UserSubscribeEvents.UserSubscribed(
            channel_id=parse_expected_value(value, "channel_id", expect_str)
        )

    # weekly-rewards

    def weekly_rewards_reward_parser(self, value) -> WeeklyRewards.Reward:
        value = expect_dict(value)
        return WeeklyRewards.Reward(
            tier=parse_expected_value(value, "tier", expect_int),
            channel_points=parse_expected_value(value, "channelPoints", expect_int),
            badge_set_id=parse_expected_value(value, "badgeSetId", expect_str),
            badge_version=parse_expected_value(value, "badgeVersion", expect_str),
        )

    def weekly_rewards_config_parser(self, value) -> WeeklyRewards.Config:
        value = expect_dict(value)
        return WeeklyRewards.Config(
            days_required_per_week=parse_expected_value(
                value, "daysRequiredPerWeek", expect_int
            )
        )

    def weekly_rewards_parser(self, value) -> WeeklyRewards.Model:
        value = expect_dict(value)
        return WeeklyRewards.Notification(
            viewer_id=parse_expected_value(value, "viewerId", expect_str),
            channel_id=parse_expected_value(value, "channelId", expect_str),
            event_id=parse_expected_value(value, "eventId", expect_str),
            days_visited_this_week=parse_expected_value(
                value, "daysVisitedThisWeek", expect_int
            ),
            accumulated_weeks=parse_value(value, "accumulatedWeeks", expect_int),
            notification_type=parse_expected_value(
                value, "notificationType", expect_str
            ),
            current_reward=parse_expected_value(
                value, "currentReward", self.weekly_rewards_reward_parser
            ),
            event_config=parse_expected_value(
                value, "eventConfig", self.weekly_rewards_config_parser
            ),
        )

    # viewer-milestones
    def streak_recovered_parser(self, value) -> ViewerMilestones.StreakRecovered:
        return ViewerMilestones.StreakRecovered(
            channel_id=parse_expected_value(value, "channel_id", expect_str)
        )

    def viewer_milestones_parser(self, value) -> ViewerMilestones.Model | None:
        value = expect_dict(value)
        type = parse_expected_value(value, "type", expect_str)
        if type == "streak-recovered":
            return self.streak_recovered_parser(
                parse_expected_value(value, "data", expect_dict)
            )
        else:
            logger.debug(f"Unknown viewer-milestones type: {type}")
            return None

    # All
    def message_parser(self, data, topic: str) -> Model | None:
        parser = self.parsers.get(topic, None)
        if parser is None:
            return None
        else:
            return parser(data)
