import datetime
from TwitchChannelPointsMiner.classes.entities.predictions.Result import Result
from TwitchChannelPointsMiner.classes.websocket.data.Predictions import (
    Prediction as WSPrediction,
)
from TwitchChannelPointsMiner.utils.Utils import simple_repr


class Prediction:
    """A Prediction on an Outcome in a Prediction Event"""

    def __init__(
        self,
        _id: str,
        channel_id: str,
        event_id: str,
        outcome_id: str,
        points: int,
        predicted_at: datetime.datetime,
        updated_at: datetime.datetime,
        user_id: str,
        user_display_name: str | None,
        result: Result | None,
    ):
        self.id = _id
        """The id of this Prediction"""
        self.channel_id = channel_id
        """The id of the channel hosting the PredictionEvent"""
        self.event_id = event_id
        """The id of the PredictionEvent on which this Prediction was placed"""
        self.outcome_id = outcome_id
        """The id of the Outcome on which this Prediction was placed"""
        self.points = points
        """The total number of points staked"""
        self.predicted_at = predicted_at
        """The initial prediction time"""
        self.updated_at = updated_at
        """The last time this Prediction was updated"""
        self.user_id = user_id
        """The id of the user that placed this Prediction"""
        self.user_display_name = user_display_name
        """The display name of the user"""
        self.result = result
        """The result, if any"""

    def update(self, other: WSPrediction):
        """
        Updates this Prediction using Twitch's WebSocket data.
        :param other: The data.
        """
        self.points = other.points
        self.updated_at = other.updated_at
        if other.result is not None:
            self.result = Result.from_ws(other.result)

    @classmethod
    def from_ws(cls, prediction: WSPrediction):
        return cls(
            _id=prediction.id,
            channel_id=prediction.channel_id,
            event_id=prediction.event_id,
            outcome_id=prediction.outcome_id,
            points=prediction.points,
            predicted_at=prediction.predicted_at,
            updated_at=prediction.updated_at,
            user_id=prediction.user_id,
            user_display_name=prediction.user_display_name,
            result=(
                Result.from_ws(prediction.result)
                if prediction.result is not None
                else None
            ),
        )

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Prediction):
            return False
        return (
            self.id == value.id
            and self.channel_id == value.channel_id
            and self.event_id == value.event_id
            and self.outcome_id == value.outcome_id
            and self.points == value.points
            and self.predicted_at == value.predicted_at
            and self.updated_at == value.updated_at
            and self.user_id == value.user_id
            and self.user_display_name == value.user_display_name
            and self.result == value.result
        )

    def __repr__(self) -> str:
        return simple_repr(self)
