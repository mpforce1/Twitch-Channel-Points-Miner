import abc
import logging
from typing import Any

from TwitchChannelPointsMiner.classes.events.Event import (
    BonusPointsAvailable,
    BonusPointsClaim,
    ChangingWatchSlots,
    ChatMention,
    CommunityGoalContribution,
    DropClaim,
    DropClaimAvailable,
    DropProgress,
    Error,
    Event,
    GainForClaim,
    GainForPrediction,
    GainForRaid,
    GainForRefund,
    GainForWatch,
    GainForWatchStreak,
    GainForWeeklyRewards,
    GainPoints,
    GiftSubReceived,
    JoinRaid,
    MomentClaim,
    MomentClaimAvailable,
    PredictionEventClosed,
    PredictionEventCreated,
    PredictionEventUpdated,
    PredictionFilters,
    PredictionLose,
    PredictionRefund,
    PredictionWin,
    StreamDown,
    StreamUp,
    StreamViewCount,
    WatchStreakMissing,
    WatchStreakProgress,
    WatchStreakRecovery,
    PredictionMade,
    WeeklyRewardsUpdate,
)
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler

logger = logging.getLogger(__name__)


class DispatchHandler(EventHandler, abc.ABC):
    """A handler that dispatches Events to specific methods based on the Event's type."""

    def __init__(self):
        # Use Any here as we know this should be correct
        self._method_cache: dict[Events, Any] = {
            Events.STREAMER_ONLINE: self.handle_stream_up,
            Events.STREAMER_OFFLINE: self.handle_stream_down,
            Events.STREAM_VIEW_COUNT: self.handle_stream_view_count,
            Events.BONUS_POINTS_AVAILABLE: self.handle_bonus_points_available,
            Events.GAIN_FOR_OTHER: self.handle_gain_points,
            Events.GAIN_FOR_RAID: self.handle_gain_for_raid,
            Events.GAIN_FOR_CLAIM: self.handle_gain_for_raid,
            Events.GAIN_FOR_WATCH: self.handle_gain_for_watch,
            Events.GAIN_FOR_WATCH_STREAK: self.handle_gain_for_watch_streak,
            Events.GAIN_FOR_WEEKLY_REWARDS: self.handle_gain_for_weekly_rewards,
            Events.GAIN_FOR_PREDICTION: self.handle_gain_for_prediction,
            Events.GAIN_FOR_REFUND: self.handle_gain_for_refund,
            Events.WATCH_STREAK_PROGRESS: self.handle_watch_streak_progress,
            Events.WATCH_STREAK_MISSING: self.handle_watch_streak_missing,
            Events.WATCH_STREAK_RECOVERY: self.handle_watch_streak_recovery,
            Events.WEEKLY_REWARDS_UPDATE: self.handle_weekly_rewards_update,
            Events.PREDICTION_EVENT_START: self.handle_prediction_event_created,
            Events.PREDICTION_EVENT_UPDATE: self.handle_prediction_event_updated,
            Events.PREDICTION_EVENT_CLOSED: self.handle_prediction_event_closed,
            Events.PREDICTION_WIN: self.handle_prediction_win,
            Events.PREDICTION_LOSE: self.handle_prediction_lose,
            Events.PREDICTION_REFUND: self.handle_prediction_refund,
            Events.MOMENT_CLAIM_AVAILABLE: self.handle_moment_claim_available,
            Events.DROP_STATUS: self.handle_drop_progress,
            Events.DROP_CLAIM_AVAILABLE: self.handle_drop_claim_available,
            Events.CHAT_MENTION: self.handle_chat_mention,
            Events.GIFT_SUB_RECEIVED: self.handle_gift_sub_received,
            Events.JOIN_RAID: self.handle_join_raid,
            Events.BONUS_CLAIM: self.handle_bonus_points_claim,
            Events.MOMENT_CLAIM: self.handle_moment_claim,
            Events.DROP_CLAIM: self.handle_drop_claim,
            Events.PREDICTION_MADE: self.handle_prediction_made,
            Events.PREDICTION_FILTERS: self.handle_prediction_filters,
            Events.CHANGING_WATCH_SLOTS: self.handle_changing_watch_slots,
            Events.COMMUNITY_GOAL_CONTRIBUTION: self.handle_community_goal_contribution,
            Events.ERROR: self.handle_error,
        }

    def handle_stream_up(self, event: StreamUp):
        pass

    def handle_stream_down(self, event: StreamDown):
        pass

    def handle_stream_view_count(self, event: StreamViewCount):
        pass

    def handle_bonus_points_available(self, event: BonusPointsAvailable):
        pass

    def handle_gain_points(self, event: GainPoints):
        pass

    def handle_gain_for_raid(self, event: GainForRaid):
        pass

    def handle_gain_for_claim(self, event: GainForClaim):
        pass

    def handle_gain_for_watch(self, event: GainForWatch):
        pass

    def handle_gain_for_watch_streak(self, event: GainForWatchStreak):
        pass

    def handle_gain_for_weekly_rewards(self, event: GainForWeeklyRewards):
        pass

    def handle_gain_for_prediction(self, event: GainForPrediction):
        pass

    def handle_gain_for_refund(self, event: GainForRefund):
        pass

    def handle_watch_streak_progress(self, event: WatchStreakProgress):
        pass

    def handle_watch_streak_missing(self, event: WatchStreakMissing):
        pass

    def handle_watch_streak_recovery(self, event: WatchStreakRecovery):
        pass

    def handle_weekly_rewards_update(self, event: WeeklyRewardsUpdate):
        pass

    def handle_prediction_event_created(self, event: PredictionEventCreated):
        pass

    def handle_prediction_event_updated(self, event: PredictionEventUpdated):
        pass

    def handle_prediction_event_closed(self, event: PredictionEventClosed):
        pass

    def handle_prediction_win(self, event: PredictionWin):
        pass

    def handle_prediction_lose(self, event: PredictionLose):
        pass

    def handle_prediction_refund(self, event: PredictionRefund):
        pass

    def handle_moment_claim_available(self, event: MomentClaimAvailable):
        pass

    def handle_drop_progress(self, event: DropProgress):
        pass

    def handle_drop_claim_available(self, event: DropClaimAvailable):
        pass

    def handle_chat_mention(self, event: ChatMention):
        pass

    def handle_gift_sub_received(self, event: GiftSubReceived):
        pass

    def handle_join_raid(self, event: JoinRaid):
        pass

    def handle_bonus_points_claim(self, event: BonusPointsClaim):
        pass

    def handle_moment_claim(self, event: MomentClaim):
        pass

    def handle_drop_claim(self, event: DropClaim):
        pass

    def handle_prediction_made(self, event: PredictionMade):
        pass

    def handle_prediction_filters(self, event: PredictionFilters):
        pass

    def handle_changing_watch_slots(self, event: ChangingWatchSlots):
        pass

    def handle_community_goal_contribution(self, event: CommunityGoalContribution):
        pass

    def handle_error(self, event: Error):
        pass

    def handle(self, event: Event):
        if event.type not in self._method_cache:
            logger.error(f"Unable to find handler method for {event.type}")
        else:
            self._method_cache[event.type](event)
