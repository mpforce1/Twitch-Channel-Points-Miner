from dataclasses import dataclass


@dataclass
class StreakRecovered:
    channel_id: str


ViewerMilestones = StreakRecovered
