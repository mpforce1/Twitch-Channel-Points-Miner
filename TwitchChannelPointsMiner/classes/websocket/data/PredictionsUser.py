from dataclasses import dataclass
from datetime import datetime

from TwitchChannelPointsMiner.classes.websocket.data.Predictions import Prediction


@dataclass
class PredictionMade:
    timestamp: datetime
    prediction: Prediction


@dataclass
class PredictionResult:
    timestamp: datetime
    prediction: Prediction


Model = PredictionMade | PredictionResult
