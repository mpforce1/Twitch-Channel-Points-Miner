import abc

from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Event import (
    Event,
)
from TwitchChannelPointsMiner.classes.events.Events import Events


class EventHandler(abc.ABC):
    @abc.abstractmethod
    def handles(self) -> Events:
        """Returns a union of the Events this Handler can handle."""
        pass

    @abc.abstractmethod
    def handle(self, event: Event):
        pass


class EventHandlerFactory(abc.ABC):
    @abc.abstractmethod
    def create(
        self, streamers: list[Streamer], prediction_events: dict[str, PredictionEvent]
    ) -> EventHandler:
        pass
