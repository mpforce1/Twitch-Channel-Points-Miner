from dataclasses import dataclass


@dataclass
class RaidUpdate:
    id: str
    target_id: str
    target_username: str
    target_display_name: str


Model = RaidUpdate
