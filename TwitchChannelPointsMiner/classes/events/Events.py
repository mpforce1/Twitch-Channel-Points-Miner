from enum import Flag, auto
from functools import reduce


class Events(Flag):
    # Twitch State Changes
    #  Streamer
    STREAMER_ONLINE = auto()
    STREAMER_OFFLINE = auto()
    STREAM_VIEW_COUNT = auto()
    #  Points
    BONUS_POINTS_AVAILABLE = auto()
    GAIN_FOR_RAID = auto()
    GAIN_FOR_CLAIM = auto()
    GAIN_FOR_WATCH = auto()
    GAIN_FOR_WATCH_STREAK = auto()
    GAIN_FOR_WEEKLY_REWARDS = auto()
    GAIN_FOR_PREDICTION = auto()
    GAIN_FOR_REFUND = auto()
    GAIN_FOR_OTHER = auto()
    POINTS_SPENT = auto()
    #  Watch Streak
    WATCH_STREAK_PROGRESS = auto()
    WATCH_STREAK_MISSING = auto()
    WATCH_STREAK_RECOVERY = auto()
    #  Weekly Rewards
    WEEKLY_REWARDS_UPDATE = auto()
    #  Predictions
    PREDICTION_EVENT_START = auto()
    PREDICTION_EVENT_UPDATE = auto()
    PREDICTION_EVENT_CLOSED = auto()
    PREDICTION_WIN = auto()
    PREDICTION_LOSE = auto()
    PREDICTION_REFUND = auto()
    PREDICTION_FAILED = auto()
    #  Moments
    MOMENT_CLAIM_AVAILABLE = auto()
    #  Drops
    DROP_STATUS = auto()
    DROP_CLAIM_AVAILABLE = auto()
    #  Chat
    CHAT_MENTION = auto()
    #  Subscriptions
    GIFT_SUB_RECEIVED = auto()

    # Miner Actions
    JOIN_RAID = auto()
    BONUS_CLAIM = auto()
    MOMENT_CLAIM = auto()
    DROP_CLAIM = auto()
    PREDICTION_MADE = auto()
    PREDICTION_FILTERS = auto()
    CHANGING_WATCH_SLOTS = auto()
    COMMUNITY_GOAL_CONTRIBUTION = auto()
    SHUTDOWN = auto()

    # Other
    ERROR = auto()

    # Unions
    GAIN_POINTS = (
        GAIN_FOR_RAID
        | GAIN_FOR_CLAIM
        | GAIN_FOR_WATCH
        | GAIN_FOR_WATCH_STREAK
        | GAIN_FOR_WEEKLY_REWARDS
        | GAIN_FOR_PREDICTION
        | GAIN_FOR_REFUND
        | GAIN_FOR_OTHER
    )
    """Gaining channel points."""
    PREDICTIONS = (
        PREDICTION_EVENT_START
        | PREDICTION_EVENT_UPDATE
        | PREDICTION_EVENT_CLOSED
        | PREDICTION_WIN
        | PREDICTION_LOSE
        | PREDICTION_REFUND
        | PREDICTION_MADE
        | PREDICTION_FILTERS
        | PREDICTION_FAILED
    )

    @staticmethod
    def gain_for(reason: str):
        match reason:
            case "RAID":
                return Events.GAIN_FOR_RAID
            case "CLAIM":
                return Events.GAIN_FOR_CLAIM
            case "WATCH":
                return Events.GAIN_FOR_WATCH
            case "WATCH_STREAK":
                return Events.GAIN_FOR_WATCH_STREAK
            case "WEEKLY_REWARDS":
                return Events.GAIN_FOR_WEEKLY_REWARDS
            case "PREDICTION":
                return Events.GAIN_FOR_PREDICTION
            case _:
                # Default to catch all type
                return Events.GAIN_POINTS

    @staticmethod
    def union(events: list["Events"]) -> "Events":
        if len(events) == 0:
            raise ValueError("At least 1 Events type must be provided")
        return reduce(lambda l, r: l | r, events[1:], events[0])

    @staticmethod
    def all():
        return Events.union([e for e in Events])

    @staticmethod
    def none():
        return Events.all() & ~Events.all()

    @staticmethod
    def default():
        """
        Gets a union of Events that's all Events except a few less useful events.
        """
        return (
            Events.all()
            & ~Events.STREAM_VIEW_COUNT
            & ~Events.BONUS_POINTS_AVAILABLE
            & ~Events.MOMENT_CLAIM_AVAILABLE
            & ~Events.PREDICTION_EVENT_UPDATE
            & ~Events.DROP_CLAIM_AVAILABLE
            & ~Events.CHANGING_WATCH_SLOTS
        )
