from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Events import Events


# Args
@dataclass(kw_only=True)
class ArgNone(TypedDict):
    pass


@dataclass(kw_only=True)
class ArgStreamer(TypedDict):
    streamer: Streamer


@dataclass(kw_only=True)
class ArgCount(TypedDict):
    count: int | float


@dataclass(kw_only=True)
class ArgTitle(TypedDict):
    title: str


@dataclass(kw_only=True)
class ArgOutcome(ArgTitle):
    odds: int | float


@dataclass(kw_only=True)
class ArgUserPrediction(TypedDict):
    outcome_title: str
    outcome_odds: int | float
    stake: int


@dataclass(kw_only=True)
class ArgTotalPoints(TypedDict):
    total_points: int


@dataclass(kw_only=True)
class ArgTime(TypedDict):
    time: datetime


@dataclass(kw_only=True)
class ArgStatus(TypedDict):
    status: str


@dataclass(kw_only=True)
class ArgStake(TypedDict):
    stake: int


@dataclass(kw_only=True)
class ArgConditional(TypedDict):
    conditional: str


@dataclass(kw_only=True)
class ArgPoints(TypedDict):
    points: int

@dataclass(kw_only=True)
class ArgResultWin(ArgPoints):
    profit: int

@dataclass(kw_only=True)
class ArgErrorCode(TypedDict):
    error_code: str


@dataclass(kw_only=True)
class ArgPrediction(TypedDict):
    title: str
    odds: float | int
    points: int


@dataclass(kw_only=True)
class ArgDrop(TypedDict):
    drop: Drop


@dataclass(kw_only=True)
class ArgRecipient(TypedDict):
    recipient: str


@dataclass(kw_only=True)
class ArgValue(TypedDict):
    value: str


@dataclass(kw_only=True)
class ArgStreamers(TypedDict):
    streamers: str


@dataclass(kw_only=True)
class ArgReason(TypedDict):
    reason: str


@dataclass(kw_only=True)
class ArgType(TypedDict):
    type: str


@dataclass(kw_only=True)
class ArgError(TypedDict):
    error: Exception


@dataclass(kw_only=True)
class ArgWinningOutcome(TypedDict):
    outcome: str


@dataclass(kw_only=True)
class ArgDropsDrop(TypedDict):
    name: str
    benefit: str
    current_minutes_watched: int
    minutes_required: int
    percentage_progress: int


@dataclass(kw_only=True)
class ArgChatMention(ArgStreamer, TypedDict):
    actor: str
    message: str


@dataclass(kw_only=True)
class ArgNotEnoughPoints(TypedDict):
    channel_points: int
    minimum_points: int | None


@dataclass(kw_only=True)
class ArgGainPoints(TypedDict):
    amount: int
    streamer: Streamer
    reason: str


@dataclass(kw_only=True)
class ArgStreamerAndCount(ArgStreamer, ArgCount):
    pass


@dataclass(kw_only=True)
class ArgWeeklyRewardsUpdate(ArgStreamer):
    update_type: str
    days_visited_this_week: int
    days: str


@dataclass(kw_only=True)
class ArgEventCreated(ArgStreamer, ArgTitle):
    prediction_window_seconds: int | float
    outcomes: str


@dataclass(kw_only=True)
class ArgPredictionMade(ArgTitle):
    points: str
    outcome_title: str
    total_update: str


@dataclass(kw_only=True)
class ArgEventUpdated(ArgStreamer, ArgTitle, ArgStatus):
    remaining: int | float
    outcomes: str


@dataclass(kw_only=True)
class ArgFilters(ArgTitle, ArgStreamer):
    reason: str


@dataclass(kw_only=True)
class ArgPredictionResult(ArgStreamer, ArgTitle):
    winning_outcome: str
    user_prediction: str
    user_result: str


@dataclass(kw_only=True)
class ArgDropWithStreamer(TypedDict):
    drop: str
    with_streamer: str


@dataclass(kw_only=True)
class ArgTier(TypedDict):
    tier: int


@dataclass(kw_only=True)
class ArgGiftSubReceived(ArgStreamer, TypedDict):
    recipient: str
    tier: str
    gifter: str
    ends_at: datetime
    days: str


@dataclass(kw_only=True)
class ArgChangingWatchSlots(TypedDict):
    adding: str
    dropping: str


@dataclass(kw_only=True)
class ArgCommunityGoalContribution(ArgStreamer, ArgTitle, TypedDict):
    points: str


@dataclass(kw_only=True)
class ArgErrorOccurred(TypedDict):
    context: str
    message: str
    error_str: str


@dataclass(kw_only=True)
class ArgJoinRaid(ArgStreamer, TypedDict):
    target: str


# Formatters
@dataclass(kw_only=True)
class StaticString:
    value: str

    def format(self):
        return self.value


@dataclass(kw_only=True)
class Requires[TArg]:
    value: str

    def format(self, kwargs: TArg):
        return self.value.format(**kwargs)


@dataclass(kw_only=True)
class Pluralizable[TArg: ArgCount]:
    singular: Requires[TArg]
    plural: Requires[TArg]

    def format(self, plural: bool, kwargs: TArg):
        if plural:
            return self.singular.format(kwargs)
        else:
            return self.plural.format(kwargs)


@dataclass(kw_only=True)
class Optional[TArg]:
    some: Requires[TArg]
    """The translation to use when the value exists"""
    none: StaticString
    """The translation to use when the value doesn't exist"""


# Groups
@dataclass(kw_only=True)
class General:
    account: str
    channel: str
    title: str
    window: str
    outcomes: str


@dataclass(kw_only=True)
class GainPoints:
    reason: Optional[ArgReason]
    main: Requires[ArgGainPoints]


@dataclass(kw_only=True)
class WeeklyRewardsUpdate:
    days: Pluralizable[ArgCount]
    main: Requires[ArgWeeklyRewardsUpdate]


@dataclass(kw_only=True)
class PredictionMade:
    points: Pluralizable[ArgCount]
    total_update: Optional[ArgTotalPoints]
    main: Requires[ArgPredictionMade]


@dataclass(kw_only=True)
class Reasons:
    too_short: Requires[ArgTime]
    not_enough_points: Requires[ArgNotEnoughPoints]
    not_active: Requires[ArgStatus]
    below_minimum: Requires[ArgStake]
    settings: Requires[ArgConditional]


@dataclass(kw_only=True)
class Filters:
    reasons: Reasons
    main: Requires[ArgFilters]


@dataclass(kw_only=True)
class UserResult:
    win: Requires[ArgResultWin]
    lose: Requires[ArgPoints]
    refund: str
    main: Requires[ArgType]


@dataclass(kw_only=True)
class PredictionResult:
    winning_outcome: Optional[ArgWinningOutcome]
    user_prediction: Requires[ArgUserPrediction]
    user_result: UserResult
    main: Requires[ArgPredictionResult]


@dataclass(kw_only=True)
class Predictions:
    outcome_simple: Requires[ArgTitle]
    outcome: Requires[ArgOutcome]
    outcome_multiline: Requires[ArgOutcome]
    event_created: Requires[ArgEventCreated]
    prediction_made: PredictionMade
    filters: Filters
    event_update: Requires[ArgEventUpdated]
    prediction_result: PredictionResult
    prediction_failed: Requires[ArgErrorCode]
    your_prediction: str
    prediction_multiline: Requires[ArgPrediction]
    winning_outcome: str
    result: str
    profit_loss: str


@dataclass(kw_only=True)
class Drops:
    drop: Requires[ArgDropsDrop]
    progress: Requires[ArgDropWithStreamer]
    with_streamer: Optional[ArgStreamer]
    claim_available: Requires[ArgDropWithStreamer]
    claim: Requires[ArgDrop]


@dataclass(kw_only=True)
class GiftSubReceived:
    from_: str
    subscription: str
    ends_at: str
    duration: str
    tier: Requires[ArgTier]
    gifter: Optional[ArgValue]
    days: Pluralizable[ArgCount]
    main: Requires[ArgGiftSubReceived]


@dataclass(kw_only=True)
class ChangingWatchSlots:
    streamer: Requires[ArgStreamer]
    adding: Optional[ArgStreamers]
    dropping: Optional[ArgStreamers]
    main: Requires[ArgChangingWatchSlots]


@dataclass(kw_only=True)
class CommunityGoalContribution:
    points: Pluralizable[ArgCount]
    main: Requires[ArgCommunityGoalContribution]


@dataclass(kw_only=True)
class Error:
    error_str: Optional[ArgError]
    occurred: Requires[ArgErrorOccurred]


# Top level model
@dataclass(kw_only=True)
class Translation:
    general: General
    names: dict[Events, str]
    stream_up: Requires[ArgStreamer]
    stream_down: Requires[ArgStreamer]
    stream_view_count: Pluralizable[ArgStreamerAndCount]
    streamer_online: Requires[ArgStreamer]
    streamer_offline: Requires[ArgStreamer]
    bonus_points_available: Requires[ArgStreamer]
    gain_points: GainPoints
    points_spent: Pluralizable[ArgStreamerAndCount]
    watch_streak_progress: Requires[ArgStreamer]
    watch_streak_missing: Requires[ArgStreamer]
    watch_streak_recovery: Requires[ArgStreamer]
    weekly_rewards_update: WeeklyRewardsUpdate
    predictions: Predictions
    moment_claim_available: Requires[ArgStreamer]
    drops: Drops
    chat_mention: Requires[ArgChatMention]
    gift_sub_received: GiftSubReceived
    join_raid: Requires[ArgJoinRaid]
    bonus_points_claim: Requires[ArgStreamer]
    moment_claim: Requires[ArgStreamer]
    changing_watch_slots: ChangingWatchSlots
    community_goal_contribution: CommunityGoalContribution
    shutdown: Requires[ArgReason]
    error: Error
