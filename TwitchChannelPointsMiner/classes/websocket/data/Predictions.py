from dataclasses import dataclass
from datetime import datetime

@dataclass
class User:
    id: str
    display_name: str

@dataclass
class Result:
    type: str
    points_won: int | None


@dataclass
class Prediction:
    id: str
    event_id: str
    outcome_id: str
    channel_id: str
    points: int
    predicted_at: datetime
    updated_at: datetime
    user_id: str
    result: Result | None
    user_display_name: str | None


@dataclass
class Outcome:
    id: str
    color: str
    title: str
    total_points: int
    total_users: int
    top_predictors: list[Prediction]


@dataclass
class PredictionEvent:
    id: str
    channel_id: str
    created_at: datetime
    created_by: User
    ended_at: datetime | None
    ended_by: User | None
    locked_at: datetime | None
    locked_by: User | None
    outcomes: list[Outcome]
    prediction_window_seconds: int
    status: str
    title: str
    winning_outcome_id: str | None
