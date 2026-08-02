from TwitchChannelPointsMiner.classes.entities.Bet import OutcomeKeys
from TwitchChannelPointsMiner.classes.entities.predictions.Prediction import Prediction
from TwitchChannelPointsMiner.utils.Utils import float_round, simple_repr
from TwitchChannelPointsMiner.classes.websocket.data.Predictions import (
    Outcome as WSOutcome,
)


class Outcome:
    """An option in a Prediction Event."""

    def __init__(
        self,
        _id: str,
        color: str,
        title: str,
        total_points: int,
        total_users: int,
        top_predictors: list[Prediction],
        percentage_users: float = 0,
        odds: float = 0,
        odds_percentage: float = 0,
        top_points: int = 0,
    ):
        self.id = _id
        """The identity"""
        self.color = color
        """The Twitch UI color"""
        self.title = title
        """The title"""
        self.total_points = total_points
        """The total number of channel points wagered"""
        self.total_users = total_users
        """The total number of users with a Prediction"""
        self.top_predictors = top_predictors
        """The top (10) Predictions with the largest stakes"""
        self.percentage_users = percentage_users
        """The proportion total users is relative to the whole event"""
        self.odds = odds
        """The odds calculated as event total points divided by outcome total_points"""
        self.odds_percentage = odds_percentage
        """The odds percentage calculated as the inverse of 100 divided by odds"""
        self.top_points = top_points
        """The most points wagered in a Prediction"""

    def compute_values(self, event_total_users: int, event_total_points: int):
        """
        Computes the calculated values for this Outcome (percentage_users, odds, odds_percentage, and top_points).
        :param event_total_users: The total number of users with a Prediction in the event.
        :param event_total_points: The total number of points wagered in the event.
        """
        self.percentage_users = (
            float_round(100 * (self.total_users / event_total_users))
            if event_total_users != 0
            else 0
        )
        self.odds = (
            float_round(event_total_points / self.total_points)
            if self.total_points != 0
            else 0
        )
        self.odds_percentage = float_round(100 / self.odds) if self.odds != 0 else 0
        self.top_points = max(map(lambda p: p.points, self.top_predictors), default=0)

    def update(
        self, ws_outcome: WSOutcome, event_total_users: int, event_total_points: int
    ):
        """
        Updates the Outcome based on the WebSocket data and the event totals.

        :param ws_outcome: The WebSocket Outcome data.
        :param event_total_users: The total number of users with a Prediction on the parent event.
        :param event_total_points: The total number of points wagered in Predictions on the parent event.
        """
        # Completely redo top predictors as it won't necessarily contain the same entries
        self.top_predictors.clear()
        for ws_predictor in ws_outcome.top_predictors:
            self.top_predictors.append(Prediction.from_ws(ws_predictor))

        self.compute_values(
            event_total_users=event_total_users, event_total_points=event_total_points
        )

    def get_value(self, key: OutcomeKeys):
        """
        Returns the value for the given key.

        :param key: The key for which to get the value.
        :return: The value for the given key.
        :raises KeyError: If an unknown key type is given.
        """
        match key:
            case OutcomeKeys.PERCENTAGE_USERS:
                return self.percentage_users
            case OutcomeKeys.ODDS_PERCENTAGE:
                return self.odds_percentage
            case OutcomeKeys.ODDS:
                return self.odds
            case OutcomeKeys.TOP_POINTS:
                return self.top_points
            case OutcomeKeys.TOTAL_USERS | OutcomeKeys.DECISION_USERS:
                return self.total_users
            case OutcomeKeys.TOTAL_POINTS | OutcomeKeys.DECISION_POINTS:
                return self.top_points
            case _:
                raise KeyError(f"Unhandled OutcomeKeys type: {key}")

    @classmethod
    def from_ws(cls, outcome: WSOutcome):
        return cls(
            _id=outcome.id,
            color=outcome.color,
            title=outcome.title,
            total_points=outcome.total_points,
            total_users=outcome.total_users,
            top_predictors=[
                Prediction.from_ws(prediction) for prediction in outcome.top_predictors
            ],
        )

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Outcome):
            return False
        return (
            self.id == value.id
            and self.color == value.color
            and self.title == value.title
            and self.total_points == value.total_points
            and self.total_users == value.total_users
            and self.top_predictors == value.top_predictors
            and self.percentage_users == value.percentage_users
            and self.odds == value.odds
            and self.odds_percentage == value.odds_percentage
            and self.top_points == value.top_points
        )

    def __repr__(self) -> str:
        return simple_repr(self)
