import abc
import datetime
from dataclasses import dataclass, field

from TwitchChannelPointsMiner.classes.StreamerSelector import weekly_rewards
from TwitchChannelPointsMiner.classes.entities.Bet import FilterCondition
from TwitchChannelPointsMiner.classes.entities.CommunityGoal import CommunityGoal
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.Raid import Raid
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.Bet import Bet
from TwitchChannelPointsMiner.classes.entities.predictions.Prediction import Prediction
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.gql.data.response.WeeklyRewards import WeeklyRewards
from TwitchChannelPointsMiner.utils.Utils import simple_repr


@dataclass(kw_only=True)
class Event(abc.ABC):
    type: Events
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
    )


@dataclass(kw_only=True)
class ChannelEvent(Event, abc.ABC):
    streamer: Streamer


# Twitch State Changes
#  Streamer
@dataclass(kw_only=True)
class StreamUp(ChannelEvent):
    type: Events = Events.STREAMER_ONLINE


@dataclass(kw_only=True)
class StreamDown(ChannelEvent):
    type: Events = Events.STREAMER_OFFLINE


@dataclass(kw_only=True)
class StreamViewCount(ChannelEvent):
    view_count: int
    type: Events = Events.STREAM_VIEW_COUNT


#  Points
@dataclass(kw_only=True)
class BonusPointsAvailable(ChannelEvent):
    claim_id: str
    amount: int
    type: Events = Events.BONUS_POINTS_AVAILABLE


@dataclass(kw_only=True)
class GainPoints(ChannelEvent):
    """This can be used when unknown reasons are encountered. Otherwise, the more specific subclasses should be used."""

    amount: int
    balance: int
    reason: str
    type: Events = Events.GAIN_FOR_OTHER


@dataclass(kw_only=True)
class GainForRaid(GainPoints):
    reason: str = "RAID"
    type: Events = Events.GAIN_FOR_RAID


@dataclass(kw_only=True)
class GainForClaim(GainPoints):
    reason: str = "CLAIM"
    type: Events = Events.GAIN_FOR_CLAIM


@dataclass(kw_only=True)
class GainForWatch(GainPoints):
    reason: str = "WATCH"
    type: Events = Events.GAIN_FOR_WATCH


@dataclass(kw_only=True)
class GainForWatchStreak(GainPoints):
    reason: str = "WATCH_STREAK"
    type: Events = Events.GAIN_FOR_WATCH_STREAK


@dataclass(kw_only=True)
class GainForWeeklyRewards(GainPoints):
    reason: str = "WEEKLY_REWARDS"
    type: Events = Events.GAIN_FOR_WEEKLY_REWARDS


@dataclass(kw_only=True)
class WatchStreakProgress(ChannelEvent):
    type: Events = Events.WATCH_STREAK_PROGRESS


@dataclass(kw_only=True)
class WatchStreakMissing(ChannelEvent):
    type: Events = Events.WATCH_STREAK_MISSING


@dataclass(kw_only=True)
class WatchStreakRecovery(ChannelEvent):
    type: Events = Events.WATCH_STREAK_RECOVERY

@dataclass(kw_only=True)
class WeeklyRewardsUpdate(ChannelEvent):
    weekly_rewards: WeeklyRewards
    update_type: str
    type: Events = Events.WEEKLY_REWARDS_UPDATE

@dataclass(kw_only=True)
class PointsSpent(ChannelEvent):
    amount: int
    balance: int
    type: Events = Events.POINTS_SPENT


#  Predictions
@dataclass(kw_only=True)
class PredictionEventEvent(ChannelEvent):
    prediction_event: PredictionEvent


@dataclass(kw_only=True)
class PredictionEventCreated(PredictionEventEvent):
    type: Events = Events.PREDICTION_EVENT_START


@dataclass(kw_only=True)
class PredictionEventUpdated(PredictionEventEvent):
    type: Events = Events.PREDICTION_EVENT_UPDATE


@dataclass(kw_only=True)
class PredictionEventClosed(PredictionEventEvent):
    type: Events = Events.PREDICTION_EVENT_UPDATE


@dataclass(kw_only=True)
class PredictionResult(PredictionEventEvent, abc.ABC):
    pass


@dataclass(kw_only=True)
class PredictionWin(PredictionResult):
    type: Events = Events.PREDICTION_WIN


@dataclass(kw_only=True)
class PredictionLose(PredictionResult):
    type: Events = Events.PREDICTION_LOSE


@dataclass(kw_only=True)
class PredictionRefund(PredictionResult):
    type: Events = Events.PREDICTION_REFUND


@dataclass(kw_only=True)
class PredictionFailed(PredictionEventEvent):
    error_code: str
    type: Events = Events.PREDICTION_FAILED


#  Moments


@dataclass(kw_only=True)
class MomentClaimAvailable(ChannelEvent):
    type: Events = Events.MOMENT_CLAIM_AVAILABLE


#  Drops
@dataclass(kw_only=True)
class DropEvent(Event):
    streamer: Streamer | None
    drop: Drop


@dataclass(kw_only=True)
class DropProgress(DropEvent):
    progress: int
    type: Events = Events.DROP_STATUS


@dataclass(kw_only=True)
class DropClaimAvailable(Event):
    streamer: Streamer | None
    drop: Drop | str
    type: Events = Events.DROP_CLAIM_AVAILABLE


#  Chat


@dataclass(kw_only=True)
class ChatMention(ChannelEvent):
    actor: str
    message: str
    type: Events = Events.CHAT_MENTION


#  Subscriptions
@dataclass(kw_only=True)
class GiftSubReceived(ChannelEvent):
    type: Events = Events.GIFT_SUB_RECEIVED


# Miner Actions
@dataclass(kw_only=True)
class JoinRaid(ChannelEvent):
    raid: Raid
    target_username: str
    # The target may not be a managed streamer, so the username is the best we can do
    type: Events = Events.JOIN_RAID


@dataclass(kw_only=True)
class BonusPointsClaim(ChannelEvent):
    type: Events = Events.BONUS_CLAIM


@dataclass(kw_only=True)
class MomentClaim(ChannelEvent):
    moment_id: str
    type: Events = Events.MOMENT_CLAIM


@dataclass(kw_only=True)
class DropClaim(DropEvent):
    type: Events = Events.DROP_CLAIM


@dataclass(kw_only=True)
class PredictionMade(PredictionEventEvent):
    prediction: Prediction
    amount: int
    type: Events = Events.PREDICTION_MADE


class FilterReason(abc.ABC):
    def __repr__(self) -> str:
        return simple_repr(self)


@dataclass(kw_only=True)
class EventTooShort(FilterReason):
    """The event was too short for the user's"""

    prediction_time: datetime.datetime


@dataclass(kw_only=True)
class NotEnoughPoints(FilterReason):
    """The user doesn't have enough channel points"""

    channel_points: int
    minimum_points: int | None


@dataclass(kw_only=True)
class PredictionAlreadyMade(FilterReason):
    """A prediction has already been made on this event"""

    pass


@dataclass(kw_only=True)
class EventNotActive(FilterReason):
    """The event is no longer active"""

    status: str


@dataclass(kw_only=True)
class PredictionPointsBelowMinimum(FilterReason):
    """The desired amount of points for the bet is below the minimum (0)"""

    bet: Bet


@dataclass(kw_only=True)
class SettingsFiltered(FilterReason):
    """The bet was filtered by the streamer's settings"""

    condition: FilterCondition
    compared_value: int | float


@dataclass(kw_only=True)
class PredictionFilters(PredictionEventEvent):
    reason: FilterReason
    type: Events = Events.PREDICTION_FILTERS


@dataclass(kw_only=True)
class ChangingWatchSlots(Event):
    adding: list[Streamer]
    dropping: list[Streamer]
    type: Events = Events.CHANGING_WATCH_SLOTS


@dataclass(kw_only=True)
class CommunityGoalContribution(ChannelEvent):
    goal: CommunityGoal
    amount: int
    type: Events = Events.COMMUNITY_GOAL_CONTRIBUTION


# Other


@dataclass(kw_only=True)
class Error(Event):
    context: str
    message: str
    error: Exception | None
    type: Events = Events.ERROR


# Utility functions


def gain_for(
    timestamp: datetime.datetime,
    reason: str,
    streamer: Streamer,
    amount: int,
    balance: int,
):
    """
    Utility function that gets the specific subclass of GainPoints Event for the given reason code.
    :param reason: The reason code.
    :param streamer: The streamer.
    :param amount: The amount of points gained.
    :param balance: The new balance.
    :return: The Event.
    """
    match reason:
        case "RAID":
            return GainForRaid(
                timestamp=timestamp,
                streamer=streamer,
                amount=amount,
                balance=balance,
            )
        case "CLAIM":
            return GainForClaim(
                timestamp=timestamp,
                streamer=streamer,
                amount=amount,
                balance=balance,
            )
        case "WATCH":
            return GainForWatch(
                timestamp=timestamp,
                streamer=streamer,
                amount=amount,
                balance=balance,
            )
        case "WATCH_STREAK":
            return GainForWatchStreak(
                timestamp=timestamp,
                streamer=streamer,
                amount=amount,
                balance=balance,
            )
        case "WEEKLY_REWARDS":
            return GainForWeeklyRewards(
                timestamp=timestamp,
                streamer=streamer,
                amount=amount,
                balance=balance,
            )
        case _:
            return GainPoints(
                timestamp=timestamp,
                streamer=streamer,
                amount=amount,
                balance=balance,
                reason=reason,
            )


def prediction_result_for(
    _type: str,
    streamer: Streamer,
    prediction_event: PredictionEvent,
) -> PredictionResult | None:
    match _type:
        case "WIN":
            return PredictionWin(
                streamer=streamer,
                prediction_event=prediction_event,
            )
        case "LOSE":
            return PredictionLose(
                streamer=streamer,
                prediction_event=prediction_event,
            )
        case "REFUND":
            return PredictionRefund(
                streamer=streamer,
                prediction_event=prediction_event,
            )
        case _:
            return None
