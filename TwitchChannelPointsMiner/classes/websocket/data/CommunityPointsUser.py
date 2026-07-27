from datetime import datetime
from dataclasses import dataclass


@dataclass
class PointsEarned:
    timestamp: datetime
    channel_id: str
    amount: int
    reason: str
    balance: int


@dataclass
class PointsSpent:
    timestamp: datetime
    channel_id: str
    balance: int


@dataclass
class ClaimAvailable:
    timestamp: datetime
    channel_id: str
    claim_id: str
    amount: int


Model = PointsEarned | PointsSpent | ClaimAvailable
