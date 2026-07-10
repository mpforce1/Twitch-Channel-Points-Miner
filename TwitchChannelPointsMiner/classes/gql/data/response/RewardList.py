from datetime import datetime


class ViewerMilestone:
    def __init__(
        self,
        _id: str,
        value: str,
        achievement_timestamp: datetime | None,
        share_status: str,
    ):
        self.id = _id  # Empty string if this is a new streak
        self.value = value  # Not sure why this is a string when it's always a number
        self.achievement_timestamp = (
            achievement_timestamp  # None if this is a new streak
        )
        self.share_status = share_status

    def __repr__(self):
        return f"ViewerMilestone({self.__dict__})"


class WatchStreakMilestone:
    def __init__(
        self,
        viewer_milestone: ViewerMilestone,
        threshold: int,
        copo_bonus: int,
        state: str,
        missed_streams: set[str] | None,
        expires_at: datetime | None,
    ):
        self.viewer_milestone = viewer_milestone
        self.threshold = threshold
        self.copo_bonus = copo_bonus
        self.state = state
        self.missed_streams = missed_streams if missed_streams is not None else set[str]()
        self.expires_at = expires_at

    def __repr__(self):
        return f"WatchStreakMilestone({self.__dict__})"


class Channel:
    class SelfEdge:
        def __init__(self, watch_streak_milestone: WatchStreakMilestone | None):
            self.watch_streak_milestone = watch_streak_milestone

        def __repr__(self):
            return f"ChannelSelfEdge({self.__dict__})"

    def __init__(self, _id: str, _self: SelfEdge):
        self.id = _id
        self.self = _self

    def __repr__(self):
        return f"Channel({self.__dict__})"


class RewardListResponse:
    def __init__(self, channel: Channel):
        self.channel = channel

    def __repr__(self):
        return f"RewardListResponse({self.__dict__})"
