from TwitchChannelPointsMiner.classes.websocket.data.Predictions import (
    Result as WSResult,
)
from TwitchChannelPointsMiner.utils.Utils import simple_repr


class Result:
    """The Result of a Prediction"""

    def __init__(self, _type: str, points_won: int | None):
        self.type = _type
        """The result type (WIN, LOSE, REFUND)"""
        self.points_won = points_won
        """The number of points won or None"""

    @classmethod
    def from_ws(cls, result: WSResult):
        return cls(
            _type=result.type,
            points_won=result.points_won,
        )

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Result):
            return False
        return self.type == value.type and self.points_won == value.points_won

    def __repr__(self) -> str:
        return simple_repr(self)
