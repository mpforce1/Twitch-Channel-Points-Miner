import abc

from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Event import Event


class EventTransformer[Result](abc.ABC):
    """Transforms Events into a different format."""

    @abc.abstractmethod
    def transform(self, event: Event) -> Result:
        """
        Transforms an Event into a Result.
        :param event: The Event to transform.
        :return: The transformed Result.
        """
        pass


class EventTransformerFactory[Result](abc.ABC):
    @abc.abstractmethod
    def create(
        self, streamers: list[Streamer], prediction_events: dict[str, PredictionEvent]
    ) -> EventTransformer[Result]:
        pass
