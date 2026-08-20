import copy
import datetime
import shutil
from dataclasses import dataclass
from typing import Callable, Literal

import pytz
from emoji import emojize

from TwitchChannelPointsMiner.classes.Translator import Translator
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
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
    EventNotActive,
    EventTooShort,
    FilterReason,
    GainPoints,
    GiftSubReceived,
    JoinRaid,
    MomentClaim,
    MomentClaimAvailable,
    NotEnoughPoints,
    PointsSpent,
    PredictionEventClosed,
    PredictionEventCreated,
    PredictionEventUpdated,
    PredictionFailed,
    PredictionFilters,
    PredictionMade,
    PredictionPointsBelowMinimum,
    PredictionResult,
    SettingsFiltered,
    Shutdown,
    StreamDown,
    StreamUp,
    StreamerOffline,
    StreamerOnline,
    StreamViewCount,
    WatchStreakMissing,
    WatchStreakProgress,
    WatchStreakRecovery,
    WeeklyRewardsUpdate,
)
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.classes.translator.Model import (
    ArgPoints,
    Requires,
    Translation,
)
from TwitchChannelPointsMiner.logger import ColorPalette

Transformation = tuple[str, str | None]


def prepend_emoji(message: str, emoji: str | None):
    """
    Prepends an emoji to the given message.
    :param message: The message.
    :param emoji: The emoji, or None.
    :return: The new message.
    """
    if emoji is None:
        return message
    else:
        return emojize(f"{emoji}  {message}")


def _weekly_rewards_update_emoji(event: WeeklyRewardsUpdate):
    emojis = [
        ":seedling:",
        ":potted_plant:",
        ":wilted_flower:",
        ":rose:",
        ":bouquet:",
    ]
    current_tier = event.weekly_rewards.current_reward.tier
    # Default emoji for if Twitch starts doing longer events
    return emojis[current_tier] if current_tier < len(emojis) else ":calendar:"


def _setup_default_emojis():
    emojis: dict[Events, str | Callable[[Event], str]] = {
        Events.STREAM_UP: ":up_arrow:",
        Events.STREAM_DOWN: ":down_arrow:",
        Events.STREAM_VIEW_COUNT: ":input_numbers:",
        Events.STREAMER_ONLINE: ":partying_face:",
        Events.STREAMER_OFFLINE: ":sleeping_face:",
        Events.BONUS_POINTS_AVAILABLE: "🪎",  # Treasure chest, currently no short code
        Events.POINTS_SPENT: ":chart_with_downwards_trend:",
        Events.WATCH_STREAK_PROGRESS: ":fire:",
        Events.WATCH_STREAK_MISSING: ":red_question_mark:",
        Events.WATCH_STREAK_RECOVERY: ":ambulance:",
        Events.WEEKLY_REWARDS_UPDATE: _weekly_rewards_update_emoji,  # pyright: ignore [reportAssignmentType]
        Events.MOMENT_CLAIM_AVAILABLE: ":video_camera:",
        Events.DROP_STATUS: ":package:",
        Events.DROP_CLAIM_AVAILABLE: ":package:",
        Events.CHAT_MENTION: ":speech_baloon:",
        Events.GIFT_SUB_RECEIVED: ":wrapped_gift:",
        Events.JOIN_RAID: ":performing_arts:",
        Events.BONUS_CLAIM: ":wrapped_gift:",
        Events.MOMENT_CLAIM: ":video_camera:",
        Events.DROP_CLAIM: ":package:",
        Events.PREDICTION_FILTERS: ":pushpin:",
        Events.CHANGING_WATCH_SLOTS: ":eyes:",
        Events.COMMUNITY_GOAL_CONTRIBUTION: ":goal_net:",
        Events.SHUTDOWN: ":stop_sign:",
        Events.ERROR: ":warning:",
    }

    for event in Events.GAIN_POINTS:
        emojis[event] = ":rocket:"

    for event in Events.PREDICTIONS & ~Events.PREDICTION_FILTERS:
        emojis[event] = ":four_leaf_clover:"
    return emojis


default_emojis = _setup_default_emojis()

miner_default_emoji = ":pick:"


class EmojiTransformer(EventTransformer[str]):
    def __init__(
        self,
        default: str = miner_default_emoji,
        emojis: dict[Events, str] | None = None,
    ):
        self.default = default
        # Start with the default emoji
        self._emojis = copy.deepcopy(default_emojis)
        if emojis is not None:
            # Override with user settings
            for events, emoji in emojis.items():
                # Handle unions
                for event in events:
                    self._emojis[event] = emoji

    def transform(self, event: Event):
        emoji = self._emojis.get(event.type, self.default)
        if isinstance(emoji, str):
            return emojize(emoji)
        else:
            return emoji(event)


@dataclass
class LineConfig:
    max_length: int | Literal["console"] | None


class TranslatorTransformer(EventTransformer[str]):
    """Transformer that turns events into human-readable strings"""

    def __init__(
        self,
        translator: Translator,
        account_username: str,
        locale: str | None = None,
        to_strs: dict[Events, Callable] | None = None,
    ):
        self.translator = translator
        self.account_username = account_username
        self.locale = locale
        # Set up defaults
        self.to_strs: dict[Events, Callable] = {
            Events.STREAM_UP: self.stream_up,
            Events.STREAM_DOWN: self.stream_down,
            Events.STREAM_VIEW_COUNT: self.stream_view_count,
            Events.STREAMER_ONLINE: self.streamer_online,
            Events.STREAMER_OFFLINE: self.streamer_offline,
            Events.BONUS_POINTS_AVAILABLE: self.bonus_points_available,
            Events.WATCH_STREAK_PROGRESS: self.watch_streak_progress,
            Events.WATCH_STREAK_MISSING: self.watch_streak_missing,
            Events.WATCH_STREAK_RECOVERY: self.watch_streak_recovery,
            Events.WEEKLY_REWARDS_UPDATE: self.weekly_rewards_update,
            Events.POINTS_SPENT: self.points_spent,
            Events.PREDICTION_EVENT_START: self.prediction_event_created,
            Events.PREDICTION_EVENT_UPDATE: self.prediction_event_updated,
            Events.PREDICTION_FAILED: self.prediction_failed,
            Events.MOMENT_CLAIM_AVAILABLE: self.moment_claim_available,
            Events.DROP_STATUS: self.drop_progress,
            Events.DROP_CLAIM_AVAILABLE: self.drop_claim_available,
            Events.CHAT_MENTION: self.chat_mention,
            Events.GIFT_SUB_RECEIVED: self.gift_sub_received,
            Events.JOIN_RAID: self.join_raid,
            Events.BONUS_CLAIM: self.bonus_points_claim,
            Events.MOMENT_CLAIM: self.moment_claim,
            Events.DROP_CLAIM: self.drop_claim,
            Events.PREDICTION_MADE: self.prediction_made,
            Events.PREDICTION_FILTERS: self.prediction_filters,
            Events.CHANGING_WATCH_SLOTS: self.changing_watch_slots,
            Events.COMMUNITY_GOAL_CONTRIBUTION: self.community_goal_contribution,
            Events.SHUTDOWN: self.shutdown,
            Events.ERROR: self.error,
        }

        for event in Events.GAIN_POINTS:
            self.to_strs[event] = self.gain_points

        for event in Events.PREDICTION_RESULT:
            self.to_strs[event] = self.prediction_result

        if to_strs is not None:
            # Add overrides
            for events, override in to_strs.items():
                for event in events:
                    self.to_strs[event] = override

    def stream_up(self, event: StreamUp):
        return self.translator.translate(
            lambda t: t.stream_up, locale=self.locale, arg={"streamer": event.streamer}
        )

    def stream_down(self, event: StreamDown):
        return self.translator.translate(
            lambda t: t.stream_down,
            locale=self.locale,
            arg={"streamer": event.streamer},
        )

    def stream_view_count(self, event: StreamViewCount):
        return self.translator.translate_plural(
            lambda t: t.stream_view_count,
            locale=self.locale,
            arg={
                "count": event.view_count,
                "streamer": event.streamer,
            },
        )

    def streamer_online(self, event: StreamerOnline):
        return self.translator.translate(
            lambda t: t.streamer_online,
            locale=self.locale,
            arg={"streamer": event.streamer},
        )

    def streamer_offline(self, event: StreamerOffline):
        return self.translator.translate(
            lambda t: t.streamer_offline,
            locale=self.locale,
            arg={"streamer": event.streamer},
        )

    def bonus_points_available(self, event: BonusPointsAvailable):
        return self.translator.translate(
            lambda t: t.bonus_points_available,
            locale=self.locale,
            arg={"streamer": event.streamer},
        )

    def gain_points(self, event: GainPoints):
        return self.translator.translate(
            lambda t: t.gain_points,
            locale=self.locale,
            arg={
                "amount": event.amount,
                "reason": event.reason,
                "streamer": event.streamer,
            },
        )

    def points_spent(self, event: PointsSpent):
        return self.translator.translate_plural(
            lambda t: t.points_spent,
            locale=self.locale,
            arg={
                "count": event.amount,
                "streamer": event.streamer,
            },
        )

    def watch_streak_progress(self, event: WatchStreakProgress):
        return self.translator.translate(
            lambda t: t.watch_streak_progress,
            locale=self.locale,
            arg={
                "streamer": event.streamer,
            },
        )

    def watch_streak_missing(self, event: WatchStreakMissing):
        return self.translator.translate(
            lambda t: t.watch_streak_missing,
            locale=self.locale,
            arg={
                "streamer": event.streamer,
            },
        )

    def watch_streak_recovery(self, event: WatchStreakRecovery):
        return self.translator.translate(
            lambda t: t.watch_streak_recovery,
            locale=self.locale,
            arg={
                "streamer": event.streamer,
            },
        )

    def weekly_rewards_update(self, event: WeeklyRewardsUpdate):
        rewards = event.weekly_rewards
        days_str = self.translator.translate_plural(
            lambda t: t.weekly_rewards_update.days,
            locale=self.locale,
            arg={"count": rewards.event_config.days_required_per_week},
        )
        return self.translator.translate(
            lambda t: t.weekly_rewards_update.main,
            locale=self.locale,
            arg={
                "streamer": event.streamer,
                "update_type": event.update_type,
                "days_visited_this_week": rewards.days_visited_this_week,
                "days": days_str,
            },
        )

    def prediction_event_created(self, event: PredictionEventCreated):
        prediction_event = event.prediction_event
        outcomes_str = self.translator.translate_list(
            lambda t: t.predictions.outcome_simple,
            [{"title": outcome.title} for outcome in prediction_event.outcomes],
            self.locale,
        )
        return self.translator.translate(
            lambda t: t.predictions.event_created,
            locale=self.locale,
            arg={
                "streamer": event.streamer,
                "prediction_window_seconds": prediction_event.prediction_window_seconds,
                "title": prediction_event.title,
                "outcomes": outcomes_str,
            },
        )

    def moment_claim_available(self, event: MomentClaimAvailable):
        return self.translator.translate(
            lambda t: t.moment_claim_available,
            locale=self.locale,
            arg={"streamer": event.streamer},
        )

    def _drop_and_streamer(self, drop: Drop | str, streamer: Streamer | None):
        streamer_str = self.translator.translate_optional(
            lambda t: t.drops.with_streamer,
            streamer,
            locale=self.locale,
            get_args=lambda s: {"streamer": s},
        )
        if isinstance(drop, str):
            drop_str = drop
        else:
            drop_str = self.translator.translate(
                lambda t: t.drops.drop,
                locale=self.locale,
                arg={
                    "name": drop.name,
                    "benefit": drop.benefit,
                    "current_minutes_watched": drop.current_minutes_watched,
                    "minutes_required": drop.minutes_required,
                    "percentage_progress": drop.percentage_progress,
                },
            )
        return drop_str, streamer_str

    def drop_progress(self, event: DropProgress):
        # TODO better info once drops system reworked
        drop_str, streamer_str = self._drop_and_streamer(event.drop, event.streamer)
        return self.translator.translate(
            lambda t: t.drops.progress,
            locale=self.locale,
            arg={
                "drop": drop_str,
                "with_streamer": streamer_str,
            },
        )

    def drop_claim_available(self, event: DropClaimAvailable):
        drop_str, streamer_str = self._drop_and_streamer(event.drop, event.streamer)
        return self.translator.translate(
            lambda t: t.drops.claim_available,
            locale=self.locale,
            arg={
                "drop": drop_str,
                "with_streamer": streamer_str,
            },
        )

    def chat_mention(self, event: ChatMention):
        return self.translator.translate(
            lambda t: t.chat_mention,
            locale=self.locale,
            arg={
                "actor": event.actor,
                "streamer": event.streamer,
                "message": event.message,
            },
        )

    def gift_sub_received(self, event: GiftSubReceived):
        streamer = event.streamer
        gift_sub = streamer.gift_sub
        if gift_sub is None:
            raise ValueError(
                f"GiftSubReceived received but unable to find Gift Sub for {streamer}"
            )
        if isinstance(gift_sub.tier, str):
            raise ValueError(f"Unable to represent non-standard Gift Subs")
        # Get ends at in user timezone
        # TODO should the timezone be configurable
        ends_at = gift_sub.ends_at.astimezone(datetime.datetime.now().tzinfo)
        days = (gift_sub.ends_at - datetime.datetime.now(tz=datetime.timezone.utc)).days

        gifter_display_name_str = self.translator.translate_optional(
            lambda t: t.gift_sub_received.gifter,
            gift_sub.gifter,
            get_args=lambda g: {"value": g.display_name},
            locale=self.locale,
        )

        days_str = self.translator.translate_plural(
            lambda t: t.gift_sub_received.days, locale=self.locale, arg={"count": days}
        )

        return self.translator.translate(
            lambda t: t.gift_sub_received.main,
            locale=self.locale,
            arg={
                "recipient": self.account_username,
                "tier": gift_sub.tier,
                "gifter": gifter_display_name_str,
                "streamer": streamer,
                "ends_at": ends_at,
                "days": days_str,
            },
        )

    def join_raid(self, event: JoinRaid):
        return self.translator.translate(
            lambda t: t.join_raid,
            locale=self.locale,
            arg={
                "streamer": event.streamer,
                "target": event.target_username,
            },
        )

    def bonus_points_claim(self, event: BonusPointsClaim):
        return self.translator.translate(
            lambda t: t.bonus_points_claim,
            locale=self.locale,
            arg={"streamer": event.streamer},
        )

    def moment_claim(self, event: MomentClaim):
        return self.translator.translate(
            lambda t: t.moment_claim,
            locale=self.locale,
            arg={"streamer": event.streamer},
        )

    def drop_claim(self, event: DropClaim):
        return self.translator.translate(
            lambda t: t.drops.claim, locale=self.locale, arg={"drop": event.drop}
        )

    def prediction_made(self, event: PredictionMade):
        # TODO we're reacting to all predictions made generally, should we only react to predictions placed by the miner
        data = event.prediction_event
        outcome = data.outcome(event.prediction.outcome_id)
        points_str = self.translator.translate_plural(
            lambda t: t.predictions.prediction_made.points,
            locale=self.locale,
            arg={"count": event.amount},
        )
        change = event.amount - event.previous_amount
        # A prediction can be added to multiple times,
        # display both the amount placed this time and the total placed if this is an update
        total_update_str = self.translator.translate_optional(
            lambda t: t.predictions.prediction_made.total_update,
            event.amount if change != 0 else None,
            locale=self.locale,
            get_args=lambda p: {"total_points": p},
        )


        return self.translator.translate(
            lambda t: t.predictions.prediction_made.main,
            locale=self.locale,
            arg={
                "title": data.title,
                "points": points_str,
                "outcome_title": outcome.title,
                "total_update": total_update_str,
            },
        )

    def _filter_reason(self, reason: FilterReason):
        match reason:
            case EventTooShort():
                return self.translator.translate(
                    lambda t: t.predictions.filters.reasons.too_short,
                    locale=self.locale,
                    arg={
                        "time": reason.prediction_time.astimezone(
                            datetime.datetime.now().tzinfo
                        )
                    },
                )
            case NotEnoughPoints():
                return self.translator.translate(
                    lambda t: t.predictions.filters.reasons.not_enough_points,
                    locale=self.locale,
                    arg={
                        "channel_points": reason.channel_points,
                        "minimum_points": reason.minimum_points,
                    },
                )
            case EventNotActive():
                return self.translator.translate(
                    lambda t: t.predictions.filters.reasons.not_active,
                    locale=self.locale,
                    arg={"status": reason.status},
                )
            case PredictionPointsBelowMinimum():
                return self.translator.translate(
                    lambda t: t.predictions.filters.reasons.below_minimum,
                    locale=self.locale,
                    arg={"stake": reason.bet.points},
                )
            case SettingsFiltered():
                return self.translator.translate(
                    lambda t: t.predictions.filters.reasons.settings,
                    locale=self.locale,
                    arg={
                        "conditional": (
                            f"{reason.condition.where.name} {reason.condition.where.name} {reason.condition.value}: "
                            f"{reason.compared_value} {reason.condition.where.inverse().symbol} {reason.condition.value}"
                        )
                    },
                )
            case _:
                raise ValueError(f"Unhandled FilterReason: {reason}")

    def prediction_filters(self, event: PredictionFilters):
        data = event.prediction_event
        return self.translator.translate(
            lambda t: t.predictions.filters.main,
            locale=self.locale,
            arg={
                "title": data.title,
                "streamer": event.streamer,
                "reason": self._filter_reason(event.reason),
            },
        )

    def _watch_slots_streamers(self, change: list[Streamer]):
        return (
            self.translator.translate_list(
                lambda t: t.changing_watch_slots.streamer,
                [{"streamer": streamer} for streamer in change],
                self.locale,
            )
            if len(change) > 0
            else None
        )

    def changing_watch_slots(self, event: ChangingWatchSlots):
        adding_str = self.translator.translate_optional(
            lambda t: t.changing_watch_slots.adding,
            self._watch_slots_streamers(event.adding),
            locale=self.locale,
            get_args=lambda s: {"streamers": s},
        )

        dropping_str = self.translator.translate_optional(
            lambda t: t.changing_watch_slots.dropping,
            self._watch_slots_streamers(event.dropping),
            locale=self.locale,
            get_args=lambda s: {"streamers": s},
        )

        return self.translator.translate(
            lambda t: t.changing_watch_slots.main,
            locale=self.locale,
            arg={
                "adding": adding_str,
                "dropping": dropping_str,
            },
        )

    def community_goal_contribution(self, event: CommunityGoalContribution):
        streamer = event.streamer
        goal = event.goal
        points_str = self.translator.translate_plural(
            lambda t: t.community_goal_contribution.points,
            locale=self.locale,
            arg={"count": event.amount},
        )
        return self.translator.translate(
            lambda t: t.community_goal_contribution.main,
            locale=self.locale,
            arg={
                "points": points_str,
                "streamer": streamer,
                "title": goal.title,
            },
        )

    def shutdown(self, event: Shutdown):
        return self.translator.translate(
            lambda t: t.shutdown, locale=self.locale, arg={"reason": event.reason}
        )

    def error(self, event: Error):
        error_str = self.translator.translate_optional(
            lambda t: t.error.error_str,
            event.error,
            locale=self.locale,
            get_args=lambda e: {"error": e},
        )

        return self.translator.translate(
            lambda t: t.error.occurred,
            locale=self.locale,
            arg={
                "context": event.context,
                "message": event.message,
                "error_str": error_str,
            },
        )

    def _prediction_event_state(self, event):
        data = event.prediction_event

        outcomes_str = self.translator.translate_list(
            lambda t: t.predictions.outcome,
            [
                {"title": outcome.title, "odds": outcome.odds}
                for outcome in data.outcomes
            ],
            self.locale,
        )

        remaining = data.seconds_remaining(datetime.datetime.now())

        return self.translator.translate(
            lambda t: t.predictions.event_update,
            locale=self.locale,
            arg={
                "streamer": event.streamer,
                "remaining": remaining,
                "title": data.title,
                "status": data.status,
                "outcomes": outcomes_str,
            },
        )

    def prediction_event_updated(self, event: PredictionEventUpdated):
        return self._prediction_event_state(event)

    # TODO is closed meaningfully different from updated
    def prediction_event_closed(self, event: PredictionEventClosed):
        return self._prediction_event_state(event)

    def prediction_result(self, event: PredictionResult):
        data = event.prediction_event
        if data.prediction is None:
            raise ValueError(
                f"PredictionResult received but the user has not made a prediction"
            )
        if data.prediction.result is None:
            raise ValueError(
                f"PredictionResult received but the prediction has no result"
            )
        result = data.prediction.result

        # Optionally give the winning outcome if it exists
        # get the outcome as a string from the default predictions outcome translation
        winning_outcome_str = self.translator.translate_optional(
            lambda t: t.predictions.prediction_result.winning_outcome,
            data.winning_outcome(),
            locale=self.locale,
            get_args=lambda outcome: {
                "outcome": self.translator.translate(
                    lambda t: t.predictions.outcome,
                    locale=self.locale,
                    arg={
                        "title": outcome.title,
                        "odds": outcome.odds,
                    },
                )
            },
        )

        user_outcome = data.outcome(data.prediction.outcome_id)
        user_prediction_str = self.translator.translate(
            lambda t: t.predictions.prediction_result.user_prediction,
            locale=self.locale,
            arg={
                "outcome": self.translator.translate(
                    lambda t: t.predictions.outcome,
                    locale=self.locale,
                    arg={"title": user_outcome.title, "odds": user_outcome.odds},
                )
            },
        )

        user_result_str = self.translator.translate(
            lambda t: t.predictions.prediction_result.user_result,
            locale=self.locale,
            arg={"type": result.type},
        )

        get_value: Callable[[Translation], Requires[ArgPoints]]
        amount: int
        if result.type == "WIN":
            get_value = lambda t: t.predictions.prediction_result.points.win
            if data.prediction.result.points_won is None:
                raise ValueError(f"Prediction WIN Result doesn't contain points won")
            amount = data.prediction.result.points_won
        elif result.type == "LOSE":
            get_value = lambda t: t.predictions.prediction_result.points.lose
            amount = data.prediction.points
        else:
            get_value = lambda t: t.predictions.prediction_result.points.refund
            amount = data.prediction.points
        points_str = self.translator.translate(
            get_value, locale=self.locale, arg={"points": amount}
        )

        return self.translator.translate(
            lambda t: t.predictions.prediction_result.main,
            locale=self.locale,
            arg={
                "streamer": event.streamer,
                "title": data.title,
                "winning_outcome": winning_outcome_str,
                "user_prediction": user_prediction_str,
                "user_result": user_result_str,
                "points": points_str,
            },
        )

    def prediction_failed(self, event: PredictionFailed):
        return self.translator.translate(
            lambda t: t.predictions.prediction_failed,
            locale=self.locale,
            arg={"error_code": event.error_code},
        )

    def transform(self, event: Event) -> str:
        to_str = self.to_strs.get(event.type, None)
        if to_str is not None:
            return to_str(event)
        else:
            raise ValueError(f"Unhandled Event: {event}")


class TranslatorNameTransformer(EventTransformer[str]):
    """Transformer that gets the name of the event in a given locale (or the default one)"""

    def __init__(self, translator: Translator, locale: str | None = None):
        self.translator = translator
        self.locale = locale

    def transform(self, event: Event) -> str:
        return self.translator.get_translation(locale=self.locale).names[event.type]


class TimestampTransformer(EventTransformer[str]):
    """Transformer that renders the timestamp for an event in a given format"""

    def __init__(self, less: bool, timezone: str | None):
        self.less = less
        """If true a shorter date format will be used."""
        self.format = "%d/%m/%y %H:%M:%S" if self.less is False else "%d/%m %H:%M:%S"
        """The date format."""
        if timezone is None or timezone == "":
            self.timezone = None
            """The timezone in which to render dates, if None the local timezone will be used."""
        else:
            try:
                self.timezone = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                self.timezone = None

    def transform(self, event: Event) -> str:
        # Convert timestamp to transformer timezone
        timestamp = event.timestamp.astimezone(self.timezone)
        return f"{timestamp.strftime(self.format)}"


class StaticStringTransformer(EventTransformer[str]):
    """Transformer that always returns a given string."""

    def __init__(self, value: str):
        self.value = value
        """The string to return."""

    def transform(self, event: Event) -> str:
        return self.value


class TruncateTransformer(EventTransformer[str]):
    def __init__(
        self,
        base: EventTransformer[str],
        default: LineConfig | None = None,
        configs: dict[Events, LineConfig] | None = None,
    ):
        self.base = base
        """The base transformer that produces strings to be truncated"""
        self.default = default if default is not None else LineConfig(max_length=None)
        """The default way to truncate strings"""
        self.configs = configs if configs is not None else dict[Events, LineConfig]()
        """A mapping of Events to truncate method"""

    def transform(self, event: Event) -> str:
        string = self.base.transform(event)
        config = self.configs.get(event.type, None)
        if config is None:
            config = self.default
        match config.max_length:
            case "console":
                return string[: shutil.get_terminal_size()[0]]
            case int():
                return string[: config.max_length]
            case _:
                return string


class ColorPaletteTransformer(EventTransformer[str]):
    """Transformer that gets a colour code based on a ColorPalette."""

    def __init__(self, palette: ColorPalette):
        self.palette = palette
        """The ColorPalette to apply."""

    def transform(self, event: Event) -> str:
        return self.palette.get(event.type.name)


class MultiTransformer(EventTransformer[str]):
    """Transformer that applies a list of transformers and joins the result from left to right."""

    def __init__(self, *transformers: EventTransformer[str], separator: str = ""):
        self.transformers = transformers
        self.separator = separator

    def transform(self, event: Event) -> str:
        return self.separator.join(
            (transformer.transform(event) for transformer in self.transformers)
        )
