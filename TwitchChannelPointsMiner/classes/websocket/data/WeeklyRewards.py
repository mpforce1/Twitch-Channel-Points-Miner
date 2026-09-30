from TwitchChannelPointsMiner.utils.Utils import simple_repr


class Reward:
    def __init__(
        self,
        tier: int,
        channel_points: int,
        badge_set_id: str,
        badge_version: str,
    ):
        self.tier = tier
        self.channel_points = channel_points
        self.badge_set_id = badge_set_id
        self.badge_version = badge_version

    def __repr__(self) -> str:
        return simple_repr(self)

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Reward):
            return False
        return (
            self.tier == value.tier
            and self.channel_points == value.channel_points
            and self.badge_set_id == value.badge_set_id
            and self.badge_version == value.badge_version
        )


class Config:
    def __init__(self, days_required_per_week: int):
        self.days_required_per_week = days_required_per_week

    def __repr__(self):
        return simple_repr(self)

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Config):
            return False
        return self.days_required_per_week == value.days_required_per_week


class Notification:
    def __init__(
        self,
        viewer_id: str,
        channel_id: str,
        event_id: str,
        days_visited_this_week: int,
        accumulated_weeks: int | None,
        notification_type: str,
        current_reward: Reward,
        event_config: Config,
    ):
        self.viewer_id = viewer_id
        self.channel_id = channel_id
        self.event_id = event_id
        self.days_visited_this_week = days_visited_this_week
        self.accumulated_weeks = accumulated_weeks
        self.notification_type = notification_type
        self.current_reward = current_reward
        self.event_config = event_config

    def __repr__(self) -> str:
        return simple_repr(self)

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Notification):
            return False
        return (
            self.viewer_id == value.viewer_id
            and self.channel_id == value.channel_id
            and self.event_id == value.event_id
            and self.days_visited_this_week == value.days_visited_this_week
            and self.accumulated_weeks == value.accumulated_weeks
            and self.notification_type == value.notification_type
            and self.current_reward == value.current_reward
            and self.event_config == value.event_config
        )

Model = Notification