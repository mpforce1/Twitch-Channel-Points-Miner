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


class Config:
    def __init__(self, days_required_per_week: int):
        self.days_required_per_week = days_required_per_week

    def __repr__(self):
        return simple_repr(self)

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
