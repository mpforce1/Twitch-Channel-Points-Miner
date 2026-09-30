from dataclasses import dataclass
from datetime import datetime


@dataclass
class StreamUp:
    timestamp: datetime

@dataclass
class StreamDown:
    timestamp: datetime


@dataclass
class ViewCount:
    timestamp: datetime
    viewers: int


Model = StreamUp | StreamDown | ViewCount
