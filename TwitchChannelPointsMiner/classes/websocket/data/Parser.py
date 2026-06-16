import logging

from TwitchChannelPointsMiner.JsonParser import (
    InvalidJsonShapeError,
    JsonParentContext,
    expect_dict,
    expect_str,
    parse_expected_value,
    dig,
)
from TwitchChannelPointsMiner.classes.websocket.data import UserSubscribeEvents
from TwitchChannelPointsMiner.classes.websocket.data.OnsiteNotification import (
    CreateNotification,
    OnsiteNotification,
    UserDropRewardReminderNotification,
    UserEarnedQuestsRewardBadgeNotification,
)
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
                f"Unable to find {ordinal(count)} wrapper markers ({wrapper}) in source: '{source}'",
            )
        if count == index:
            return source[first_wrapper_index + wrapper_len : second_wrapper_index]
        else:
            count += 1
            previous_last_bold_marker = second_wrapper_index
    raise ValueError(f"Index {index} must be greater than 0.")


class Parser:
    def __init__(self):
        self.onsite_notification_parsers = {
            "create-notification": self.parse_create_notification
        }
        self.ignorable_onsite_notification_types = ["update-summary"]
        self.create_notification_parsers = {
            "user_drop_reward_reminder_notification": self.user_drop_reward_reminder_notification_parser,
            "quests_viewer_reward_campaign_earned_badge": self.quests_viewer_reward_campaign_earned_badge_parser,
        }

    # onsite-notifications

    def user_drop_reward_reminder_notification_parser(self, notification):
        notification = expect_dict(notification)
        body = parse_expected_value(notification, "body_md", expect_str)
        with JsonParentContext("body_md"):
            # The drop name is in the first set of bold markdown tags
            drop_name = parse_wrapped_markdown_segment(body, "**")
        image_url = dig(
            notification,
            ["data_blocks", 1, "content", "image_block", "url"],
            expect_str,
        )
        return UserDropRewardReminderNotification(
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
        return UserEarnedQuestsRewardBadgeNotification(
            badge_name=badge_name,
            image_url=image_url,
        )

    def parse_create_notification(self, data) -> CreateNotification | None:
        data = expect_dict(data)
        notification = parse_expected_value(data, "notification", expect_dict)
        with JsonParentContext("notification"):
            _type = parse_expected_value(notification, "type", expect_str)
            if _type in self.create_notification_parsers:
                return self.create_notification_parsers[_type](notification)
            else:
                logger.debug(f"Unknown create-notification type: {_type}")
                return None

    def parse_onsite_notification(self, value) -> OnsiteNotification | None:
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

    def parse_user_subscribe_events(self, value) -> UserSubscribeEvents.UserSubscribed:
        value = expect_dict(value)
        return UserSubscribeEvents.UserSubscribed(
            channel_id=parse_expected_value(value, "channel_id", expect_str)
        )
