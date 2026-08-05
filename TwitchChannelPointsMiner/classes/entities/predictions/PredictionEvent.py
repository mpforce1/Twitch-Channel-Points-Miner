import datetime
from typing import Callable

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.predictions.Outcome import Outcome
from TwitchChannelPointsMiner.classes.entities.predictions.Prediction import Prediction
from TwitchChannelPointsMiner.classes.entities.predictions.User import User
from TwitchChannelPointsMiner.classes.websocket.data.Predictions import (
    PredictionEvent as WSPredictionEvent,
)


class PredictionEvent:
    """A Twitch Prediction Event"""

    def __init__(
        self,
        channel_id: str,
        event_id: str,
        title: str,
        created_at: datetime.datetime,
        created_by: User,
        locked_at: datetime.datetime | None,
        locked_by: User | None,
        ended_at: datetime.datetime | None,
        ended_by: User | None,
        prediction_window_seconds: int,
        status: str,
        winning_outcome_id: str | None,
        outcomes: list[Outcome],
        total_points: int = 0,
        total_users: int = 0,
        prediction: Prediction | None = None,
    ):
        self.channel_id = channel_id
        """The id of the channel hosting the event"""
        self.event_id = event_id
        """The id of this event"""
        self.title = title.strip()
        """The event title"""
        self.created_at = created_at
        """The date time this event was created"""
        self.created_by = created_by
        """The user that created this event"""
        self.locked_at = locked_at
        """The date time this event was locked or None"""
        self.locked_by = locked_by
        """The user that locked this event or None"""
        self.ended_at = ended_at
        """The date time this event ended or None"""
        self.ended_by = ended_by
        """The user that ended this event or None"""
        self.prediction_window_seconds: float = prediction_window_seconds
        """The duration, in seconds, that predictions can be made"""
        self.status = status
        """The status (ACTIVE, CLOSED)"""
        self.winning_outcome_id = winning_outcome_id
        """The id of the winning outcome or None"""
        self.outcomes = outcomes
        """The list of each outcome of this event"""
        self.total_points = total_points
        """The total number of points wagered on outcomes of this event"""
        self.total_users = total_users
        """The total number of users with a prediction in this event"""
        self.prediction = prediction
        """The user's prediction or None"""

    def __repr__(self):
        return f"EventPrediction(event_id={self.event_id}, channel_id={self.channel_id}, title={self.title})"

    def __str__(self):
        return (
            f"EventPrediction: {Settings.logger.anonymiser.channel_id(self.channel_id)} - {self.title}"
            if Settings.logger.less
            else self.__repr__()
        )

    def compute_totals(self):
        """
        Calculates the total points and users then updates the outcomes' computed values.
        """
        # Compute totals
        self.total_points = 0
        self.total_users = 0
        for outcome in self.outcomes:
            self.total_points += outcome.total_points
            self.total_users += outcome.total_users

        # Update outcomes
        for outcome in self.outcomes:
            outcome.compute_values(self.total_users, self.total_points)

    def update(self, event: WSPredictionEvent):
        """
        Updates this event with new data from the WebSocket.
        :param event: The event update.
        """
        # Update metadata
        self.locked_at = event.locked_at
        self.locked_by = (
            User.from_ws(event.locked_by) if event.locked_by is not None else None
        )
        self.ended_at = event.ended_at
        self.ended_by = (
            User.from_ws(event.ended_by) if event.ended_by is not None else None
        )
        self.status = event.status
        self.winning_outcome_id = event.winning_outcome_id
        self.outcomes = [Outcome.from_ws(outcome) for outcome in event.outcomes]

        # Compute totals
        self.compute_totals()

    def outcome(self, outcome_id: str):
        """
        Returns the Outcome with the given id.
        :param outcome_id: The id of the Outcome.
        :return: The Outcome.
        :raises StopIteration: If the Outcome could not be found.
        """
        return next((outcome for outcome in self.outcomes if outcome.id == outcome_id))

    def outcome_safe(self, index: int):
        """
        Gets the Outcome for the given index. If the index is out of range, returns the fist Outcome.
        :param index: The index of the Outcome.
        :return: The Outcome.
        """
        return self.outcomes[index if 0 <= index < len(self.outcomes) else 0]

    def _top_outcome_by_key(self, key: Callable[[Outcome], int | float]):
        return max(self.outcomes, key=key)

    def outcome_most_users(self):
        """Gets the Outcome with the most users."""
        return self._top_outcome_by_key(key=lambda o: o.total_users)

    def outcome_highest_odds(self):
        """Gets the Outcome with the highest odds."""
        return self._top_outcome_by_key(key=lambda o: o.odds)

    def outcome_highest_odds_percentage(self):
        """Gets the Outcome with the highest odds percentage."""
        return self._top_outcome_by_key(key=lambda o: o.odds_percentage)

    def outcome_top_points(self):
        """Gets the Outcome with the highest individual prediction."""
        return self._top_outcome_by_key(key=lambda o: o.top_points)

    def prediction_window_end_time(self):
        """
        Returns the end time of the prediction window.
        """
        return (
                self.created_at
                + datetime.timedelta(seconds=self.prediction_window_seconds)
        )

    def seconds_remaining(self, from_time: datetime.datetime):
        """
        Gets the number of seconds from the given time until the end of the prediction window.
        :param from_time: The time to measure from.
        :return: The number of seconds.
        """
        return (self.prediction_window_end_time() - from_time).total_seconds()

    def winning_outcome(self):
        if self.winning_outcome_id is None:
            return None
        return self.outcome(self.winning_outcome_id)

    def _describe_prediction_and_result(self):
        if self.prediction is None:
            prediction = "\tPrediction: None"
            result = "\tResult: None"
        else:
            outcome = self.outcome(self.prediction.outcome_id)
            prediction = (
                f"\tPrediction:"
                f"\t\tOutcome: {outcome.title}"
                f"\t\tOdds: {outcome.odds}"
                f"\t\tWager: {self.prediction.points}"
            )
            if self.prediction.result is None:
                result = "\tResult: None"
            else:
                match self.prediction.result.type:
                    case "WIN":
                        points = f"Won: +{self.prediction.result.points_won}"
                    case "LOSE":
                        points = f"Lost: -{self.prediction.points}"
                    case "REFUND":
                        points = "Refunded"
                    case _:
                        raise ValueError(
                            f"Unknown result type: {self.prediction.result.type}"
                        )
                result = f"\tResult: {points}"
        return f"{prediction}\n" f"{result}"

    def _describe(self, streamer_display_name: str):
        return (
            "Prediction Event:\n"
            f"\tStreamer: '{streamer_display_name}'\n"
            f"\tTitle: '{self.title}'\n"
            f"\tStatus: '{self.status}'\n"
        )

    def describe(self, streamer_display_name: str):
        """
        Gets a human-readable (English) string, containing a description of the event.
        Shows the outcomes, the prediction if one has been placed, and the result if the event has been resulted.
        :param streamer_display_name: The name of the Streamer for the event.
        :return: The description string.
        """
        outcomes = [f"\t\tOutcome: {outcome.title}" for outcome in self.outcomes]
        return (
            f"{self._describe(streamer_display_name)}"
            f"\tOutcomes:\n{outcomes}\n"
            f"{self._describe_prediction_and_result()}"
        )

    def describe_result(self, streamer_display_name: str):
        """
        Gets a human-readable (English) string, containing a description of the event.
        Shows the prediction and result, but not outcomes.
        :param streamer_display_name: The name of the Streamer for the event.
        :return: The description string.
        """
        return (
            f"{self._describe(streamer_display_name)}\n"
            f"{self._describe_prediction_and_result()}"
        )

    @classmethod
    def from_ws(cls, event: WSPredictionEvent):
        value = cls(
            channel_id=event.channel_id,
            event_id=event.id,
            title=event.title,
            created_at=event.created_at,
            created_by=User.from_ws(event.created_by),
            locked_at=event.locked_at,
            locked_by=(
                User.from_ws(event.locked_by) if event.locked_by is not None else None
            ),
            ended_at=event.ended_at,
            ended_by=(
                User.from_ws(event.ended_by) if event.ended_by is not None else None
            ),
            prediction_window_seconds=event.prediction_window_seconds,
            status=event.status,
            winning_outcome_id=event.winning_outcome_id,
            outcomes=[Outcome.from_ws(outcome) for outcome in event.outcomes],
        )

        # Reuse update to avoid restating how to calculate totals
        value.update(event)

        return value

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, PredictionEvent):
            return False
        return (
            self.channel_id == value.channel_id
            and self.event_id == value.event_id
            and self.title == value.title
            and self.created_at == value.created_at
            and self.created_by == value.created_by
            and self.locked_at == value.locked_at
            and self.ended_at == value.ended_at
            and self.ended_by == value.ended_by
            and self.prediction_window_seconds == value.prediction_window_seconds
            and self.status == value.status
            and self.winning_outcome_id == value.winning_outcome_id
            and self.outcomes == value.outcomes
            and self.total_points == value.total_points
            and self.total_users == value.total_users
            and self.prediction == value.prediction
        )
