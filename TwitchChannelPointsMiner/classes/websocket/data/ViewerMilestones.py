from dataclasses import dataclass


@dataclass
class StreakRecovered:
    channel_id: str


@dataclass
class StreakAchieved:
    channel_id: str
    value: str  # This is a string but it's always an int
    threshold: int


ViewerMilestonesUpdate = StreakAchieved

Model = StreakRecovered | ViewerMilestonesUpdate
