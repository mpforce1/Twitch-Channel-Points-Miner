from datetime import datetime

from TwitchChannelPointsMiner.utils.Utils import simple_repr

# Update Summary


class UnreadSummary:
    def __init__(self, count: int, last_read_all: datetime, count_by_md: dict):
        self.count = count
        self.last_read_all = last_read_all
        self.count_by_md = count_by_md

    def __repr__(self):
        return simple_repr(self)


class ReadSummary:
    def __init__(self, count: int, last_seen: datetime, count_by_md: dict[str, int]):
        self.count = count
        self.last_seen = last_seen
        self.count_by_md = count_by_md

    def __repr__(self):
        return simple_repr(self)


class Summaries:
    def __init__(self, unread: UnreadSummary, read: ReadSummary):
        self.unread = unread
        self.read = read

    def __repr__(self):
        return simple_repr(self)


class UpdateSummary:
    def __init__(
        self,
        unseen_view_count: int,
        last_seen_at: datetime,
        viewer_unread_count: int,
        creator_unread_count: int,
        safety_unread_count: int,
        summaries: dict[str, Summaries],
    ):
        self.type = "update-summary"
        self.unseen_view_count = unseen_view_count
        self.last_seen_at = last_seen_at
        self.viewer_unread_count = viewer_unread_count
        self.creator_unread_count = creator_unread_count
        self.safety_unread_count = safety_unread_count
        self.summaries = summaries

    def __repr__(self):
        return simple_repr(self)


# Create Notification


class UserDropRewardReminderNotification:
    """A notification informing the user that they've earned a new Drop."""

    def __init__(self, drop_name: str, image_url: str):
        self.drop_name = drop_name
        self.image_url = image_url

    def __repr__(self):
        return simple_repr(self)

    def __eq__(self, other):
        return (
            isinstance(other, UserDropRewardReminderNotification)
            and other.drop_name == self.drop_name
            and other.image_url == self.image_url
        )


class UserEarnedQuestsRewardBadgeNotification:
    """A notification informing the user that they've earned a new Quest badge."""

    def __init__(self, badge_name: str, image_url: str):
        self.badge_name = badge_name
        self.image_url = image_url

    def __repr__(self):
        return simple_repr(self)

    def __eq__(self, other):
        return (
            isinstance(other, UserEarnedQuestsRewardBadgeNotification)
            and other.badge_name == self.badge_name
            and other.image_url == self.image_url
        )


# Types

CreateNotification = (
    UserDropRewardReminderNotification | UserEarnedQuestsRewardBadgeNotification
)

Model = UpdateSummary | CreateNotification
