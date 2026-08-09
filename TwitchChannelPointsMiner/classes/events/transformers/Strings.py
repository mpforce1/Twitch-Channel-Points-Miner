import shutil
from dataclasses import dataclass
import datetime
from typing import Literal

import pytz
from emoji import emojize

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
    StreamViewCount,
    WatchStreakMissing,
    WatchStreakProgress,
    WatchStreakRecovery,
    WeeklyRewardsUpdate,
)
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.logger import ColorPalette
from TwitchChannelPointsMiner.utils.Utils import millify, oxford_comma_list

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


@dataclass
class LineConfig:
    max_length: int | Literal["console"] | None


class DefaultStringTransformer(EventTransformer[str]):
    """Transformer that turns events into human-readable strings"""

    def __init__(self, configs: dict[Events, LineConfig] | None = None):
        self.configs = configs if configs is not None else dict[Events, LineConfig]()


    def stream_up(self, event: StreamUp):
        return (
            f"{event.streamer} is Online!",
            ":partying_face:",
        )

    def stream_down(self, event: StreamDown):
        return (
            f"{event.streamer} is Offline!",
            ":sleeping_face:",
        )

    def stream_view_count(self, event: StreamViewCount):
        return (
            f"{event.streamer} has {event.view_count} viewers",
            ":input_numbers:",
        )

    def bonus_points_available(self, event: BonusPointsAvailable):
        return (
            f"Bonus Claim available for {event.streamer}",
            "🪎",  # Treasure chest, currently no short code
        )

    def gain_points(self, event: GainPoints):
        return (
            f"+{event.amount} → {event.streamer} - Reason: {event.reason}.",
            ":rocket:",
        )

    def watch_streak_progress(self, event: WatchStreakProgress):
        return (
            f"Detected Watch Streak for {event.streamer}",
            ":fire:",
        )

    def watch_streak_missing(self, event: WatchStreakMissing):
        return (
            f"Missing Watch Streak for {event.streamer}",
            ":red_question_mark:",
        )

    def watch_streak_recovery(self, event: WatchStreakRecovery):
        return (
            f"Watch Streak recovered for {event.streamer}",
            ":ambulance:",
        )

    def weekly_rewards_update(self, event: WeeklyRewardsUpdate):
        emojis = [
            ":seedling:",
            ":potted_plant:",
            ":wilted_flower:",
            ":rose:",
            ":bouquet:",
        ]
        streamer = event.streamer
        rewards = event.weekly_rewards
        current_tier = event.weekly_rewards.current_reward.tier
        # Default emoji for if Twitch starts doing longer events
        emoji = emojis[current_tier] if current_tier < len(emojis) else ":calendar:"
        return (
            f"Weekly Reward update for {streamer}: {event.update_type}. "
            f"{rewards.days_visited_this_week}/{rewards.event_config.days_required_per_week} days visited this week.",
            emoji,
        )

    def points_spent(self, event: PointsSpent):
        return (
            f"{event.amount} points spent for {event.streamer}",
            ":chart_with_downwards_trend:",
        )

    def prediction_event_created(self, event: PredictionEventCreated):
        prediction_event = event.prediction_event
        return (
            f"Prediction event started for {event.streamer} ({prediction_event.prediction_window_seconds}s): "
            f'"{prediction_event.title}": '
            f"[{oxford_comma_list([outcome.title for outcome in prediction_event.outcomes])}]",
            ":four_leaf_clover:",
        )

    def moment_claim_available(self, event: MomentClaimAvailable):
        return (
            f"Moment claim available for {event.streamer}",
            ":video_camera:",
        )

    def drop_progress(self, event: DropProgress):
        # TODO better info once drops system reworked
        streamer = event.streamer
        return (
            f"Drop progress for {event.drop}"
            f"{(f' for {streamer}' if streamer is not None else '')}",
            ":package:",
        )

    def drop_claim_available(self, event: DropClaimAvailable):
        streamer = event.streamer
        return (
            f"Drop claim available for {event.drop}"
            f"{(f' for {streamer}' if streamer is not None else '')}",
            ":package:",
        )

    def chat_mention(self, event: ChatMention):
        return (
            f"{event.actor} wrote at {event.streamer} wrote: {event.message}",
            ":speech_baloon:",
        )

    def gift_sub_received(self, event: GiftSubReceived):
        streamer = event.streamer
        gift_sub = streamer.gift_sub
        if gift_sub is None:
            raise ValueError(
                f"GiftSubReceived received but unable to find Gift Sub for {streamer}"
            )
        gifter_display_name = (
            gift_sub.gifter.display_name if gift_sub.gifter is not None else "Anonymous"
        )
        # Get ends at in user timezone
        ends_at = gift_sub.ends_at.astimezone(datetime.datetime.now().tzinfo)
        days = (gift_sub.ends_at - datetime.datetime.now(tz=datetime.timezone.utc)).days
        days_plural = "day" if days == 1 else "days"
        return (
            f"Tier-{gift_sub.tier} Gift Sub from {gifter_display_name} for {streamer}, "
            f"ends at {ends_at} (in {days} {days_plural})",
            ":wrapped_gift:",
        )

    def join_raid(self, event: JoinRaid):
        return (
            f"Joining raid from {event.streamer} to {event.target_username}!",
            ":performing_arts:",
        )

    def bonus_points_claim(self, event: BonusPointsClaim):
        return (
            f"Claiming the bonus for {event.streamer}!",
            ":wrapped_gift:",
        )

    def moment_claim(self, event: MomentClaim):
        return (
            f"Claiming the moment for {event.streamer}!",
            ":video_camera:",
        )

    def drop_claim(self, event: DropClaim):
        return (
            f'Claiming drop "{event.drop}"',
            ":package:",
        )

    def prediction_made(self, event: PredictionMade):
        # TODO we're reacting to all predictions made generally, should we only react to predictions placed by the miner
        data = event.prediction_event
        outcome = data.outcome(event.prediction.outcome_id)
        total_points = data.prediction.points if data.prediction is not None else 0
        # A prediction can be added to multiple times,
        # display both the amount placed this time and the total placed if this is an update
        total_update = (
            f", Total points placed: {total_points}"
            if total_points != event.amount
            else ""
        )
        return (
            f"Prediction made for {data.title}: "
            f'Placed {millify(event.amount)} channel points on: "{outcome.title}"'
            f"{total_update}",
            ":four_leaf_clover:",
        )

    def _filter_reason(self, reason: FilterReason):
        match reason:
            case EventTooShort():
                return (
                    f"Chosen prediction time is in the past "
                    f"{reason.prediction_time.astimezone(datetime.datetime.now().tzinfo)}"
                )
            case NotEnoughPoints():
                return (
                    f"You don't have enough channel points: "
                    f"{reason.channel_points} < {reason.minimum_points}"
                )
            case EventNotActive():
                return f"Event is not longer active: {reason.status}"
            case PredictionPointsBelowMinimum():
                return f"Chosen stake ({reason.bet.points}) is less than 0"
            case SettingsFiltered():
                return (
                    f"Filtered by your bet settings: "
                    f"{reason.condition.where.name} {reason.condition.where.name} {reason.condition.value}: "
                    f"{reason.compared_value} {reason.condition.where.inverse().symbol} {reason.condition.value}"
                )
            case _:
                raise ValueError(f"Unhandled FilterReason: {reason}")

    def prediction_filters(self, event: PredictionFilters):
        data = event.prediction_event
        return (
            f'Not placing a prediction on "{data.title}" for {event.streamer}: '
            f"{self._filter_reason(event.reason)}",
            ":pushpin:",
        )

    def _watch_slots(self, change: list[Streamer]):
        return oxford_comma_list([streamer.username for streamer in change])

    def changing_watch_slots(self, event: ChangingWatchSlots):
        adding = (
            f"Adding {self._watch_slots(event.adding)}" if len(event.adding) > 0 else ""
        )
        dropping = (
            f"Dropping {self._watch_slots(event.dropping)}"
            if len(event.dropping) > 0
            else ""
        )
        seperator = ", " if (adding != "" and dropping != "") else ""
        return (
            f"Changing watch slots: {adding}{seperator}{dropping}",
            ":eyes:",
        )

    def community_goal_contribution(self, event: CommunityGoalContribution):
        streamer = event.streamer
        goal = event.goal
        return (
            f"Contributed {event.amount} points to {streamer.username}'s community goal '{goal.title}'",
            ":goal_net:",
        )

    def shutdown(self, event: Shutdown):
        return (
            f"Miner stopping: {event.reason}",
            ":stop_sign:",
        )

    def error(self, event: Error):
        error_str = f": {event.error}" if event.error is not None else ""
        return (
            f"Error occurred: {event.context}: {event.message}{error_str}",
            ":warning:",
        )

    def _prediction_event_state(self, event):
        data = event.prediction_event
        return (
            f"Prediction event updated for {event.streamer} "
            f"({data.seconds_remaining(datetime.datetime.now())}s remaining): "
            f'"{data.title}"'
            f"status '{data.status}'"
            f"[{oxford_comma_list([f'{outcome.title}: {outcome.odds}' for outcome in data.outcomes])}]"
        )

    def prediction_event_updated(self, event: PredictionEventUpdated):
        return (
            self._prediction_event_state(event),
            ":four_leaf_clover:",
        )

    # TODO is closed meaningfully different from updated
    def prediction_event_closed(self, event: PredictionEventClosed):
        return (
            self._prediction_event_state(event),
            ":four_leaf_clover:",
        )

    def prediction_result(self, event: PredictionResult):
        data = event.prediction_event
        winning_outcome = data.winning_outcome()
        if data.prediction is None:
            raise ValueError(
                f"PredictionResult received but the user has not made a prediction"
            )
        if data.prediction.result is None:
            raise ValueError(
                f"PredictionResult received but the prediction has no result"
            )
        result = data.prediction.result
        return (
            f"Prediction event resulted for {event.streamer}: "
            f'"{data.title}": '
            f"\n\tWinning outcome: '{(winning_outcome.title if winning_outcome is not None else 'None')}'"
            f"\n\tUser prediction: '{data.outcome(data.prediction.outcome_id).title}'"
            f"\n\tUser Result: '{result.type}'"
            f"\n\tPoints gained: '{(result.points_won if result.points_won is not None else 0)}'",
            ":four_leaf_clover:",
        )

    def prediction_failed(self, event: PredictionFailed):
        return (
            f"Failed to place bet, error: {event.error_code}",
            ":four_leaf_clover:",
        )

    def get_transformation(self, event: Event) -> Transformation | None:
        match event:
            case StreamUp():
                return self.stream_up(event)
            case StreamDown():
                return self.stream_down(event)
            case StreamViewCount():
                return self.stream_view_count(event)
            case BonusPointsAvailable():
                return self.bonus_points_available(event)
            case GainPoints():
                return self.gain_points(event)
            case WatchStreakProgress():
                return self.watch_streak_progress(event)
            case WatchStreakMissing():
                return self.watch_streak_missing(event)
            case WatchStreakRecovery():
                return self.watch_streak_recovery(event)
            case WeeklyRewardsUpdate():
                return self.weekly_rewards_update(event)
            case PointsSpent():
                return self.points_spent(event)
            case PredictionEventCreated():
                return self.prediction_event_created(event)
            case PredictionEventUpdated():
                return self.prediction_event_updated(event)
            case PredictionResult():
                return self.prediction_result(event)
            case PredictionFailed():
                return self.prediction_failed(event)
            case MomentClaimAvailable():
                return self.moment_claim_available(event)
            case DropProgress():
                return self.drop_progress(event)
            case DropClaimAvailable():
                return self.drop_claim_available(event)
            case ChatMention():
                return self.chat_mention(event)
            case GiftSubReceived():
                return self.gift_sub_received(event)
            case JoinRaid():
                return self.join_raid(event)
            case BonusPointsClaim():
                return self.bonus_points_claim(event)
            case MomentClaim():
                return self.moment_claim(event)
            case DropClaim():
                return self.drop_claim(event)
            case PredictionMade():
                return self.prediction_made(event)
            case PredictionFilters():
                return self.prediction_filters(event)
            case ChangingWatchSlots():
                return self.changing_watch_slots(event)
            case CommunityGoalContribution():
                return self.community_goal_contribution(event)
            case Shutdown():
                return self.shutdown(event)
            case Error():
                return self.error(event)
            case _:
                return None

    def transform(self, event: Event) -> str:
        transformation = self.get_transformation(event)
        if transformation is not None:
            prepended = prepend_emoji(transformation[0], transformation[1])
            config = self.configs.get(event.type, None)
            if config is None:
                return prepended
            else:
                match config.max_length:
                    case "console":
                        return prepended[:shutil.get_terminal_size()[0]]
                    case int():
                        return prepended[:config.max_length]
                    case _:
                        return prepended
        else:
            raise ValueError(f"Unhandled Event: {event}")


class AddDateTimeTransformer(EventTransformer[str]):
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
