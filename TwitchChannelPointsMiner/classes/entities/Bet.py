import operator
from enum import Enum, auto
from typing import Any, Callable


class Strategy(Enum):
    """Enum representing a Strategy for placing Bets on EventPredictions."""

    MOST_VOTED = auto()
    """
    Selects the Outcome with the most number of users. For example:
        If Outcome A has 10 users and Outcome B has 20 users then Outcome B will be selected since 20 > 10.
    """
    HIGH_ODDS = auto()
    """
    Selects the Outcome with the highest odds. For example:
        If the odds of Outcome A are 3.1 and B are 1.2 then Outcome A would be selected since 3.1 > 1.2.
    """
    PERCENTAGE = auto()
    """
    Selects the Outcome with the greatest percentage of channel points. Similar to SMART_MONEY. For example:
        if Outcome A has a total of 150 channel points wagered and B has 50 then Outcome A would be selected since 150 > 50.
        (as a percentage that's 150 + 50 = 200 total points on the event, A has 150/200 = 75%, B has 50/200 = 25% and 75% > 25%)
    """
    SMART_MONEY = auto()
    """
    Selects the Outcome with the highest number of total channel points in a single Prediction. Similar to PERCENTAGE. For example:
        If outcome A has a total of 150 channel points wagered and B has 50 then outcome A would be selected since 150 > 50.
    """
    SMART = auto()
    """
    Works with events with 2 outcomes.
    Calculates the difference between the percentage of users on both outcomes.
    If the difference is less than the 'percentage_gap' in the streamer's BetSettings then the option with the highest odds will be selected.
    Otherwise the option with the highest total users will be selected.
    """
    NUMBER_1 = auto()
    """Selects the first outcome."""
    NUMBER_2 = auto()
    """Selects the second outcome."""
    NUMBER_3 = auto()
    """Selects the third outcome."""
    NUMBER_4 = auto()
    """Selects the fourth outcome."""
    NUMBER_5 = auto()
    """Selects the fifth outcome."""
    NUMBER_6 = auto()
    """Selects the sixth outcome."""
    NUMBER_7 = auto()
    """Selects the seventh outcome."""
    NUMBER_8 = auto()
    """Selects the eighth outcome."""
    NUMBER_9 = auto()
    """Selects the ninth outcome."""
    NUMBER_10 = auto()
    """Selects the tenth outcome."""

    def __str__(self):
        return self.name


class Condition(Enum):
    """Enum representing numeric comparisons."""

    def __init__(
        self, operator_function: Callable[[int | float, int | float], Any], symbol: str
    ):
        self.operator_function = operator_function
        self.symbol = symbol

    GT = operator.gt, ">"
    """Greater than."""
    LT = operator.lt, "<"
    """Less than."""
    GTE = operator.ge, ">="
    """Greater than or equal than."""
    LTE = operator.le, "<="
    """Less than or equal than."""

    def __str__(self):
        return self.name

    def inverse(self):
        match self:
            case Condition.GT:
                return Condition.LTE
            case Condition.LT:
                return Condition.GTE
            case Condition.GTE:
                return Condition.LT
            case Condition.LTE:
                return Condition.GT
            case _:
                raise ValueError(f"Unknown Condition: {self}")


class OutcomeKeys(str, Enum):
    """Enum representing EventPrediction and Outcome values that can be used in betting strategies."""

    PERCENTAGE_USERS = "percentage_users"
    """The percentage of users on a given outcome relative to the whole event."""
    ODDS_PERCENTAGE = "odds_percentage"
    """The estimated probability of a given outcome, calculated from the outcome's odds (probability = 1 / odds)."""
    ODDS = "odds"
    """The odds of a given outcome, calculated as the outcome's total points over the event's total points."""
    TOP_POINTS = "top_points"
    """The greatest number of points for an outcome."""
    TOTAL_USERS = "total_users"
    """The total number of users for an event/outcome."""
    TOTAL_POINTS = "total_points"
    """The total number of points for an event/outcome."""
    DECISION_USERS = "decision_users"
    """The total number of users for the decided outcome. Used to decide whether a bet should be skipped."""
    DECISION_POINTS = "decision_points"
    """The total number of points for the decided outcome. Used to decide whether a bet should be skipped."""

    def __str__(self):
        return self.name


class DelayMode(Enum):
    """
    Represents an anchor point in time from which to measure.
    This is used to decide when to place a bet relative to times in the lifecycle of a EventPrediction.
    """

    FROM_START = auto()
    """Measure time relative to the start of the event."""
    FROM_END = auto()
    """Measure time relative to the end of the event."""
    PERCENTAGE = auto()
    """
    Measure time relative to the start of the event as a percentage of the length of the event.
    e.g. If the event if 120 seconds long and the delay is 0.2 then the bet will be attempted at 0.2 * 120 = 24 seconds from the start of the event.
    """

    def __str__(self):
        return self.name


class FilterCondition(object):
    """
    An object representing a filter to use when deciding to skip bets.
    e.g.
        FilterCondition(OutcomeKeys.TOTAL_POINTS, Condition.GT, 5000)
        would mean that the given outcome needs more than 5000 total points wagered to be acceptable.
    """

    __slots__ = [
        "by",
        "where",
        "value",
    ]

    def __init__(self, by: OutcomeKeys, where: Condition, value: int | float):
        self.by = by
        """The property of the outcome to check. Should be one of the OutcomeKeys static members."""
        self.where = where
        """The type of comparison to make."""
        self.value = value
        """The value against which to compare the property."""

    def __repr__(self):
        return f"FilterCondition(by={self.by.upper()}, where={self.where}, value={self.value})"

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, FilterCondition):
            return False
        else:
            return (
                self.by == value.by
                and self.where == value.where
                and self.value == value.value
            )


class BetSettings(object):
    __slots__ = [
        "strategy",
        "percentage",
        "percentage_gap",
        "max_points",
        "minimum_points",
        "stealth_mode",
        "filter_condition",
        "delay",
        "delay_mode",
    ]

    def __init__(
        self,
        strategy: Strategy = None,
        percentage: int = None,
        percentage_gap: int = None,
        max_points: int = None,
        minimum_points: int = None,
        stealth_mode: bool = None,
        filter_condition: FilterCondition = None,
        delay: float = None,
        delay_mode: DelayMode = None,
    ):
        self.strategy = strategy
        self.percentage = percentage
        self.percentage_gap = percentage_gap
        self.max_points = max_points
        self.minimum_points = minimum_points
        self.stealth_mode = stealth_mode
        self.filter_condition = filter_condition
        self.delay = delay
        self.delay_mode = delay_mode

    def default(self):
        self.strategy = self.strategy if self.strategy is not None else Strategy.SMART
        self.percentage = self.percentage if self.percentage is not None else 5
        self.percentage_gap = (
            self.percentage_gap if self.percentage_gap is not None else 20
        )
        self.max_points = self.max_points if self.max_points is not None else 50000
        self.minimum_points = (
            self.minimum_points if self.minimum_points is not None else 0
        )
        self.stealth_mode = (
            self.stealth_mode if self.stealth_mode is not None else False
        )
        self.delay = self.delay if self.delay is not None else 6
        self.delay_mode = (
            self.delay_mode if self.delay_mode is not None else DelayMode.FROM_END
        )

    def __repr__(self):
        return f"BetSettings(strategy={self.strategy}, percentage={self.percentage}, percentage_gap={self.percentage_gap}, max_points={self.max_points}, minimum_points={self.minimum_points}, stealth_mode={self.stealth_mode}, filter={self.filter_condition})"
