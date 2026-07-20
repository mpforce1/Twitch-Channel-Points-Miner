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
    GAIN_FOR_OTHER = auto()
    POINTS_SPENT = auto()
    #  Watch Streak
    WATCH_STREAK_PROGRESS = auto()
    WATCH_STREAK_MISSING = auto()
    WATCH_STREAK_RECOVERY = auto()
    #  Predictions
    PREDICTION_EVENT_START = auto()
    PREDICTION_EVENT_UPDATE = auto()
    PREDICTION_EVENT_CLOSED = auto()
    PREDICTION_WIN = auto()
    PREDICTION_LOSE = auto()
    PREDICTION_REFUND = auto()
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
    """Predictions being skipped"""

    # Other
    ERROR = auto()

    # Unions
GAIN_POINTS = (
    Events.GAIN_FOR_RAID | Events.GAIN_FOR_CLAIM | Events.GAIN_FOR_WATCH | Events.GAIN_FOR_WATCH_STREAK
)
"""Gaining channel points."""
PREDICTIONS = (
    Events.PREDICTION_EVENT_START
    | Events.PREDICTION_EVENT_UPDATE
    | Events.PREDICTION_EVENT_CLOSED
    | Events.PREDICTION_EVENT_RESULT
    | Events.PREDICTION_WIN
    | Events.PREDICTION_LOSE
    | Events.PREDICTION_REFUND
    | Events.PREDICTION_MADE
    | Events.PREDICTION_FILTERS
)
"""All prediction related events."""
ALL = reduce(lambda e1, e2: e1 | e2, Events, Events.ERROR)
