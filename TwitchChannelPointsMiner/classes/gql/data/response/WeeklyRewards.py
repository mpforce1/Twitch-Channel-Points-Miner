from datetime import datetime
from TwitchChannelPointsMiner.utils.Utils import simple_repr


class Badge:
    def __init__(
        self,
        _id: str,
        set_id: str,
        version: str,
        title: str,
        image_1x: str,
        image_2x: str,
        image_4x: str,
        click_action: str,
        click_url: str,
    ):
        self.id = _id
        self.set_id = set_id
        self.version = version
        self.title = title
        self.image_1x = image_1x
        self.image_2x = image_2x
        self.image_4x = image_4x
        self.click_action = click_action
        self.click_url = click_url

    def __repr__(self):
        return simple_repr(self)


class RewardTier:
    def __init__(self, tier: int, channel_points: int, badge: Badge):
        self.tier = tier
        self.channel_points = channel_points
        """The amount of channel points awarded by this tier."""
        self.badge = badge

    def __repr__(self) -> str:
        return simple_repr(self)


class EventConfig:
    def __init__(
        self,
        _id: str,
        days_required_per_week: int,
        end_date: datetime,
        week_reset_dates: list[datetime],
        reward_tiers: list[RewardTier],
    ):
        self.id = _id
        self.days_required_per_week = days_required_per_week
        """The number of days in a week required to obtain each tier."""
        self.end_date = end_date
        """The end datetime of this event."""
        self.week_reset_dates = week_reset_dates
        """The end datetime of each week in this event."""
        self.reward_tiers = reward_tiers
        """Each reward tier for this event."""

    def __repr__(self):
        return simple_repr(self)


class WeeklyRewards:
    def __init__(
        self,
        days_visited_this_week: int,
        accumulated_weeks: int,
        has_earned_weekly_reward_this_week: bool,
        has_visited_today: bool,
        current_reward: RewardTier,
        event_config: EventConfig,
    ):
        self.days_visited_this_week = days_visited_this_week
        """The number of days the user has visited the stream this week."""
        self.accumulated_weeks = accumulated_weeks
        """The total number of weeks the user has already completed."""
        self.has_earned_weekly_reward_this_week = has_earned_weekly_reward_this_week
        """Whether the reward has already been obtained this week."""
        self.has_visited_today = has_visited_today
        """Whether the user has already visited today."""
        self.current_reward = current_reward
        """The next reward."""
        self.event_config = event_config
        """The configuration for this event."""

    def __repr__(self):
        return simple_repr(self)
