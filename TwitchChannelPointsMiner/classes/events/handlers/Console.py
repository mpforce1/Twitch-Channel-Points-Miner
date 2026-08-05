import sys
from dataclasses import dataclass

from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Handler import (
    EventHandler,
    EventHandlerFactory,
)
from TwitchChannelPointsMiner.classes.events.Transformer import (
    EventTransformer,
    EventTransformerFactory,
)
from TwitchChannelPointsMiner.classes.events.transformers import (
    DefaultTransformerFactory,
)


@dataclass
class ConsoleConfiguration:
    events: Events
    """The events that can be handled"""
    transformer: EventTransformerFactory[str] | EventTransformer[str] | None
    """The event to string transformer to use"""


class ConsoleHandler(EventHandler):
    """Handler that prints to stdout"""

    def __init__(self, events: Events, transformer: EventTransformer[str]):
        self.events = events
        self.transformer = transformer

    def handle(self, event: Event):
        sys.stdout.write(f"{self.transformer.transform(event)}\n")

    def handles(self) -> Events:
        return self.events


class ConsoleHandlerFactory(EventHandlerFactory):
    def __init__(self, configuration: ConsoleConfiguration | None):
        self.configuration = (
            configuration
            if configuration is not None
            else ConsoleConfiguration(
                events=Events.default(), transformer=DefaultTransformerFactory()
            )
        )

    def create(
        self, streamers: list[Streamer], prediction_events: dict[str, PredictionEvent]
    ) -> ConsoleHandler:
        if isinstance(self.configuration.transformer, EventTransformer):
            transformer = self.configuration.transformer
        else:
            if self.configuration.transformer is None:
                transformer_factory = DefaultTransformerFactory()
            else:
                transformer_factory = self.configuration.transformer
            transformer = transformer_factory.create(
                streamers=streamers, prediction_events=prediction_events
            )

        return ConsoleHandler(events=self.configuration.events, transformer=transformer)
