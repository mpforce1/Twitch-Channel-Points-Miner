from dataclasses import dataclass
from datetime import datetime


@dataclass
class Goal:
    id: str
    title: str
    is_in_stock: bool
    points_contributed: int
    goal_amount: int
    per_stream_maximum_user_contribution: int
    status: str


@dataclass
class CommunityGoalCreated:
    timestamp: datetime
    goal: Goal


@dataclass
class CommunityGoalUpdated:
    timestamp: datetime
    goal: Goal


@dataclass
class CommunityGoalDeleted:
    timestamp: datetime
    goal: Goal


Model = CommunityGoalCreated | CommunityGoalUpdated | CommunityGoalDeleted
