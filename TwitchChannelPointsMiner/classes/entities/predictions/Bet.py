class Bet:
    """Represents a Bet made for an EventPrediction Outcome. It can create a new Prediction or update an existing one."""

    __slots__ = ["outcome_id", "points"]

    def __init__(self, outcome_id: str, points: int):
        self.outcome_id = outcome_id
        """The id of the Outcome on which the bet should be placed."""
        self.points = points
        """The amount of channel points to wager."""

    def __repr__(self):
        return f"Bet(outcome_id='{self.outcome_id}', points={self.points})"

    def __eq__(self, value: object):
        return (
            isinstance(value, Bet)
            and self.outcome_id == value.outcome_id
            and self.points == value.points
        )
