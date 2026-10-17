from dataclasses import dataclass


@dataclass
class DropProgress:
    drop_id: str
    channel_id: str
    current_progress_min: int
    required_progress_min: int
    current_progress: int
    required_progress: int
    progress_type: str  # "minutes_watched"
    is_sitewide: bool

type Model = DropProgress