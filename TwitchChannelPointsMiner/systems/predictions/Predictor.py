import datetime
import logging
from threading import Timer
from typing import Callable, Protocol

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Bet import (
    BetSettings,
    DelayMode,
    OutcomeKeys,
    Strategy,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.Bet import Bet
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Event import (
    EventNotActive,
    FilterReason,
    PredictionAlreadyMade,
    PredictionFilters,
    NotEnoughPoints,
    PredictionPointsBelowMinimum,
    SettingsFiltered,
    EventTooShort,
)
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.systems.Predictions import Predictor, PredictorFactory
from TwitchChannelPointsMiner.utils.Entities import find_streamer

logger = logging.getLogger(__name__)


def create_bet(streamer: Streamer, event: PredictionEvent) -> Bet:
    """
    Create bet implementation that complies with the Streamer's settings.

    :param streamer: The Streamer for the event.
    :param event: The event.
    :return: The Bet created.
    """
    if event.prediction is not None:
        # We should have already filtered the event by this point
        raise ValueError(
            f"Unable to create bet for Prediction Event '{event.title}', Prediction already made."
        )
    settings: BetSettings = streamer.settings.bet

    match settings.strategy:
        case Strategy.MOST_VOTED:
            outcome = event.outcome_most_users()
        case Strategy.HIGH_ODDS:
            outcome = event.outcome_highest_odds()
        case Strategy.PERCENTAGE:
            outcome = event.outcome_highest_odds_percentage()
        case Strategy.SMART_MONEY:
            outcome = event.outcome_top_points()
        case Strategy.NUMBER_1:
            outcome = event.outcome_safe(0)
        case Strategy.NUMBER_2:
            outcome = event.outcome_safe(1)
        case Strategy.NUMBER_3:
            outcome = event.outcome_safe(2)
        case Strategy.NUMBER_4:
            outcome = event.outcome_safe(3)
        case Strategy.NUMBER_5:
            outcome = event.outcome_safe(4)
        case Strategy.NUMBER_6:
            outcome = event.outcome_safe(5)
        case Strategy.NUMBER_7:
            outcome = event.outcome_safe(6)
        case Strategy.NUMBER_8:
            outcome = event.outcome_safe(7)
        case Strategy.NUMBER_9:
            outcome = event.outcome_safe(8)
        case Strategy.NUMBER_10:
            outcome = event.outcome_safe(9)
        case Strategy.SMART:
            # TODO is it an oversight that SMART can only consider the first 2 options
            difference = abs(
                event.outcome_safe(0).percentage_users
                - event.outcome_safe(1).percentage_users
            )
            outcome = (
                event.outcome_highest_odds()
                if difference < settings.percentage_gap
                else event.outcome_most_users()
            )
        case _:
            raise ValueError(
                f"Unable to create bet for Prediction Event '{event.title}', invalid strategy {settings.strategy}"
            )

    balance = streamer.channel_points
    amount = min(
        int(balance * (settings.percentage / 100)),
        settings.max_points,
    )
    if settings.stealth_mode:
        amount = min(amount, outcome.top_points)

    return Bet(outcome.id, int(amount))


def skip_event(event: PredictionEvent) -> FilterReason | None:
    """
    Skip event implementation that requires the event to be active and the prediction to not already be made.
    :param event: The event to possibly skip.
    :return: The skip reason if one is found.
    """
    if event.status != "ACTIVE":
        logger.info(
            f"Oh no! The event is not active anymore! Current status: {event.status}",
            extra={
                "emoji": ":disappointed_relieved:",
                "event": Events.PREDICTION_FAILED,
            },
        )
        return EventNotActive(status=event.status)
    if event.prediction is not None:
        logger.debug(
            f"Not making a prediction on '{event.title}', prediction already made",
            extra={
                "emoji": ":disappointed_relieved:",
                "event": Events.PREDICTION_FAILED,
            },
        )
        return PredictionAlreadyMade()
    return None


def skip_bet(
    streamer: Streamer, event: PredictionEvent, bet: Bet
) -> FilterReason | None:
    """
    Skip bet implementation that abides by the Streamer's BetSettings.
    :param streamer: The Streamer for the Event.
    :param event: The Event.
    :param bet: The bet that might get skipped.
    :return: The skip reason if one can be found.
    """
    if bet.points < 0:
        return PredictionPointsBelowMinimum(bet=bet)

    settings: BetSettings = streamer.settings.bet
    if settings.filter_condition is not None:
        # key == by , condition == where
        key = settings.filter_condition.by
        condition = settings.filter_condition.where
        value = settings.filter_condition.value

        match key:
            case OutcomeKeys.TOTAL_USERS:
                compared_value = event.total_users
            case OutcomeKeys.TOTAL_POINTS:
                compared_value = event.total_points
            case _:
                # Other keys refer to values on outcomes
                compared_value = event.outcome(bet.outcome_id).get_value(key)

        # Check if condition is satisfied
        if condition.operator_function(compared_value, value):
            return None
        else:
            return SettingsFiltered(
                condition=settings.filter_condition,
                compared_value=compared_value,
            )
    else:
        # Default don't skip the bet
        return None


def get_prediction_time(
    streamer: Streamer, event: PredictionEvent
) -> datetime.datetime:
    """
    Uses the streamer's settings to calculate the moment a prediction should be placed.
    :param streamer: The streamer for the event.
    :param event: The event.
    :return: The date time a prediction should be placed.
    """
    delay_mode: DelayMode = streamer.settings.bet.delay_mode
    delay: float | int = streamer.settings.bet.delay
    match delay_mode:
        case DelayMode.FROM_START:
            # Start time plus delay, clamped to the event end time
            return event.created_at + datetime.timedelta(
                seconds=min(delay, event.prediction_window_seconds)
            )
        case DelayMode.FROM_END:
            # End time minus delay, clamped to the event start time
            return event.created_at + datetime.timedelta(
                seconds=max(event.prediction_window_seconds - delay, 0)
            )
        case DelayMode.PERCENTAGE:
            # Start time plus delay as a percentage, clamped between 0-100
            return event.created_at + datetime.timedelta(
                seconds=event.prediction_window_seconds * max(min(delay, 1), 0)
            )
        case _:
            # Default to the prediction end time
            return event.created_at + datetime.timedelta(
                seconds=event.prediction_window_seconds
            )


class TimerFactory(Protocol):
    """Factory that produces Timers"""

    def __call__(self, interval: float, function: Callable, args: list) -> Timer: ...


class BasicPredictor(Predictor):
    """A Bettor that abides by the streamer's settings to place bets."""

    def __init__(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
        event_manager: EventManager,
        timer_factory: TimerFactory | None = None,
    ):
        self.twitch = twitch
        self.streamers = streamers
        self.prediction_events = prediction_events
        self.event_manager = event_manager
        self._timer_factory: TimerFactory = (
            timer_factory if timer_factory is not None else Timer
        )

    def find_streamer(self, channel_id: str) -> Streamer | None:
        """
        Finds the Streamer with the given channel id.
        :param channel_id: The id of the Streamer.
        :return: The Streamer, or None if one couldn't be found.
        """
        try:
            return find_streamer(self.streamers, channel_id)
        except KeyError:
            return None

    def create_bet(
        self, streamer: Streamer, event: PredictionEvent
    ) -> Bet | FilterReason:
        return create_bet(streamer, event)

    def skip_event(
        self, streamer: Streamer, event: PredictionEvent
    ) -> FilterReason | None:
        return skip_event(event)

    def skip_bet(
        self, streamer: Streamer, event: PredictionEvent, bet: Bet
    ) -> FilterReason | None:
        return skip_bet(streamer, event, bet)

    def make_prediction(self, event_id: str):
        event = self.prediction_events.get(event_id, None)
        if event is None:
            logger.debug(f"Not placing bet on {event_id}, untracked event")
            return
        streamer = self.find_streamer(event.channel_id)
        if streamer is None:
            logger.debug(f"Not placing bet on '{event.title}', untracked streamer")
            return
        skip_event_reason = self.skip_event(streamer, event)
        if skip_event_reason is not None:
            self.event_manager.manage(
                PredictionFilters(
                    streamer=streamer,
                    prediction_event=event,
                    reason=skip_event_reason,
                )
            )
            return
        bet = self.create_bet(streamer, event)
        if isinstance(bet, FilterReason):
            self.event_manager.manage(
                PredictionFilters(
                    streamer=streamer,
                    prediction_event=event,
                    reason=bet,
                )
            )
            return
        skip_bet_reason = self.skip_bet(streamer, event, bet)
        if skip_bet_reason is None:
            self.twitch.make_prediction(streamer, event, bet)
        else:
            logger.info(
                f"Skip betting for the event {event} because '{skip_bet_reason}'",
                extra={
                    "emoji": ":pushpin:",
                    "event": Events.PREDICTION_FILTERS,
                },
            )
            self.event_manager.manage(
                PredictionFilters(
                    streamer=streamer,
                    prediction_event=event,
                    reason=skip_bet_reason,
                )
            )

    def get_prediction_time(
        self, streamer: Streamer, event: PredictionEvent
    ) -> datetime.datetime:
        return get_prediction_time(streamer, event)

    def event_created(self, event: PredictionEvent):
        streamer = self.find_streamer(event.channel_id)
        if streamer is None:
            logger.debug(
                f"Ignoring Prediction Event '{event.title}': Untracked Streamer"
            )
            return
        bet_settings = streamer.settings.bet
        if (
            bet_settings.minimum_points is not None
            and streamer.channel_points <= bet_settings.minimum_points
        ):
            # Reject if `minimum_points` isn't `None` and the user has fewer than that many points
            logger.info(
                f"{streamer} only has {streamer.channel_points} channel points and the minimum for predictions is: {bet_settings.minimum_points}",
                extra={"emoji": ":pushpin:", "event": Events.PREDICTION_FILTERS},
            )
            self.event_manager.manage(
                PredictionFilters(
                    streamer=streamer,
                    prediction_event=event,
                    reason=NotEnoughPoints(
                        channel_points=streamer.channel_points,
                        minimum_points=bet_settings.minimum_points,
                    ),
                )
            )
            return

        prediction_time = self.get_prediction_time(streamer, event)
        predict_after_seconds = (
            prediction_time - datetime.datetime.now(tz=datetime.timezone.utc)
        ).total_seconds()
        if predict_after_seconds <= 0:
            # Reject if we've already missed the prediction time
            logger.info(
                f"Unable to make prediction, the desired time to make the prediction ({prediction_time}) is in the past",
                extra={
                    "emoji": ":pushpin:",
                    "event": Events.PREDICTION_FILTERS,
                },
            )
            self.event_manager.manage(
                PredictionFilters(
                    streamer=streamer,
                    prediction_event=event,
                    reason=EventTooShort(
                        prediction_time=prediction_time,
                    ),
                )
            )
            return

        event_id = event.event_id
        place_bet_thread = self._timer_factory(
            predict_after_seconds,
            self.make_prediction,
            [event_id],
        )
        place_bet_thread.daemon = True
        place_bet_thread.start()

        logger.info(
            f"Place the bet after: {predict_after_seconds}s for: {self.prediction_events[event.event_id]}"
        )

    def event_updated(self, event: PredictionEvent):
        # By default, we don't need to react to this
        pass


class BasicPredictorFactory(PredictorFactory):
    def __init__(self, create_timer: TimerFactory):
        self.create_timer = create_timer

    def create(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
        event_manager: EventManager,
    ) -> Predictor:
        return BasicPredictor(
            twitch=twitch,
            streamers=streamers,
            prediction_events=prediction_events,
            event_manager=event_manager,
            timer_factory=self.create_timer,
        )
