import datetime

import pytz
from emoji import emojize

from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Event import (
    BonusPointsAvailable,
    BonusPointsClaim,
    ChangingWatchSlots,
    ChannelEvent,
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
    PredictionEventEvent,
    PredictionEventUpdated,
    PredictionFailed,
    PredictionFilters,
    PredictionMade,
    PredictionPointsBelowMinimum,
    PredictionResult,
    SettingsFiltered,
    StreamDown,
    StreamUp,
    StreamViewCount,
    WatchStreakMissing,
    WatchStreakProgress,
    WatchStreakRecovery,
)
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.logger import ColorPalette
from TwitchChannelPointsMiner.utils.Entities import find_streamer
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


class DefaultStringTransformer(EventTransformer[str]):
    """Transformer that turns events into human-readable strings"""

    def __init__(
        self, streamers: list[Streamer], prediction_events: dict[str, PredictionEvent]
    ):
        self.streamers = streamers
        self.prediction_events = prediction_events

    def find_streamer(self, event: ChannelEvent):
        return find_streamer(self.streamers, event.channel_id)

    def find_event(self, event: PredictionEventEvent):
        return self.prediction_events[event.event_id]

    def stream_up(self, event: StreamUp):
        return (
            f"{self.find_streamer(event)} is Online!",
            ":partying_face:",
        )

    def stream_down(self, event: StreamDown):
        return (
            f"{self.find_streamer(event)} is Offline!",
            ":sleeping_face:",
        )

    def stream_view_count(self, event: StreamViewCount):
        return (
            f"{self.find_streamer(event)} has {event.view_count} viewers",
            ":input_numbers:",
        )

    def bonus_points_available(self, event: BonusPointsAvailable):
        return (
            f"Bonus Claim available for {self.find_streamer(event)}",
            "🪎",  # Treasure chest, currently no short code
        )

    def gain_points(self, event: GainPoints):
        return (
            f"+{event.amount} → {self.find_streamer(event)} - Reason: {event.reason}.",
            ":rocket:",
        )

    def watch_streak_progress(self, event: WatchStreakProgress):
        return (
            f"Detected Watch Streak for {self.find_streamer(event)}",
            ":fire:",
        )

    def watch_streak_missing(self, event: WatchStreakMissing):
        return (
            f"Missing Watch Streak for {self.find_streamer(event)}",
            ":red_question_mark:",
        )

    def watch_streak_recovery(self, event: WatchStreakRecovery):
        return (
            f"Watch Streak recovered for {self.find_streamer(event)}",
            ":ambulance:",
        )

    def points_spent(self, event: PointsSpent):
        return (
            f"{event.amount} points spent for {self.find_streamer(event)}",
            ":chart_with_downwards_trend:",
        )

    def prediction_event_created(self, event: PredictionEventCreated):
        data = self.find_event(event)
        return (
            f"Prediction event started for {self.find_streamer(event)} ({data.prediction_window_seconds}s): "
            f'"{data.title}": '
            f"[{oxford_comma_list([outcome.title for outcome in data.outcomes])}]",
            ":four_leaf_clover:",
        )

    def moment_claim_available(self, event: MomentClaimAvailable):
        return (
            f"Moment claim available for {self.find_streamer(event)}",
            ":video_camera:",
        )

    def drop_progress(self, event: DropProgress):
        # TODO better info once drops system reworked
        streamer = (
            find_streamer(self.streamers, event.channel_id)
            if event.channel_id is not None
            else None
        )
        return (
            f"Drop progress for {event.drop_id}"
            f"{(f' for {streamer}' if streamer is not None else '')}",
            ":package:",
        )

    def drop_claim_available(self, event: DropClaimAvailable):
        streamer = (
            find_streamer(self.streamers, event.channel_id)
            if event.channel_id is not None
            else None
        )
        return (
            f"Drop claim available for {event.drop_id}"
            f"{(f' for {streamer}' if streamer is not None else '')}",
            ":package:",
        )

    def chat_mention(self, event: ChatMention):
        return (
            f"{event.actor} wrote at {self.find_streamer(event)} wrote: {event.message}",
            ":speech_baloon:",
        )

    def gift_sub_received(self, event: GiftSubReceived):
        streamer = self.find_streamer(event)
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
            f"Joining raid from {self.find_streamer(event)} to {event.target_username}!",
            ":performing_arts:",
        )

    def bonus_points_claim(self, event: BonusPointsClaim):
        return (
            f"Claiming the bonus for {self.find_streamer(event)}!",
            ":wrapped_gift:",
        )

    def moment_claim(self, event: MomentClaim):
        return (
            f"Claiming the moment for {self.find_streamer(event)}!",
            ":video_camera:",
        )

    def drop_claim(self, event: DropClaim):
        return (
            f'Claiming drop "{event.drop_description}"',
            ":package:",
        )

    def prediction_made(self, event: PredictionMade):
        data = self.find_event(event)
        outcome = data.outcome(event.outcome_id)
        return (
            f"Making prediction for {data.title}: "
            f'Place {millify(event.amount)} channel points on: "{outcome.title}"',
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
                return f"Chosen stake ({reason.points}) is less than 0"
            case SettingsFiltered():
                return (
                    f"Filtered by your bet settings: "
                    f"{reason.condition.where.name} {reason.condition.where.name} {reason.condition.value}: "
                    f"{reason.compared_value} {reason.condition.where.inverse().symbol} {reason.condition.value}"
                )
            case _:
                raise ValueError(f"Unhandled FilterReason: {reason}")

    def prediction_filters(self, event: PredictionFilters):
        data = self.find_event(event)
        return (
            f'Not placing a prediction on "{data.title}" for {self.find_streamer(event)}: '
            f"{self._filter_reason(event.reason)}",
            ":pushpin:",
        )

    def _watch_slots(self, change: list[str]):
        return oxford_comma_list(
            [
                find_streamer(self.streamers, channel_id).username
                for channel_id in change
            ]
        )

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
        streamer = self.find_streamer(event)
        goal = streamer.community_goals.get(event.goal_id, None)
        if goal is None:
            raise ValueError(f"No Community Goal found for id '{event.goal_id}'")
        return (
            f"Contributed {event.amount} points to community goal {goal.title}",
            ":goal_net:",
        )

    def error(self, event: Error):
        error_str = f": {event.error}" if event.error is not None else ""
        return (
            f"Error occurred: {event.context}: {event.message}{error_str}",
            ":warning:",
        )

    def _prediction_event_state(self, event):
        data = self.find_event(event)
        return (
            f"Prediction event updated for {self.find_streamer(event)} "
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
        data = self.find_event(event)
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
            f"Prediction event resulted for {self.find_streamer(event)}: "
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
            case Error():
                return self.error(event)
            case _:
                return None

    def transform(self, event: Event) -> str:
        transformation = self.get_transformation(event)
        if transformation is not None:
            return prepend_emoji(transformation[0], transformation[1])
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
