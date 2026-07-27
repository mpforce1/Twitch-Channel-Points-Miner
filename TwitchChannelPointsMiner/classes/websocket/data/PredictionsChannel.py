from dataclasses import dataclass
from datetime import datetime

from TwitchChannelPointsMiner.classes.websocket.data.Predictions import PredictionEvent


@dataclass
class EventCreated:
    timestamp: datetime
    event: PredictionEvent


@dataclass
class EventUpdated:
    timestamp: datetime
    event: PredictionEvent


Model = EventCreated | EventUpdated
