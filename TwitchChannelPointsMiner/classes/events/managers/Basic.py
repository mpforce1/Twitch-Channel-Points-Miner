from threading import Thread

from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Manager import (
    EventManager,
    EventManagerFactory,
)
from TwitchChannelPointsMiner.classes.events.managers.Ignore import IgnoreEventManager


class BasicEventManager(EventManager):
    """Basic Event Manager implementation that maintains a list of handlers and passes events to each in turn"""

    def __init__(self, handlers: list[EventHandler] | None = None):
        self.handlers = handlers if handlers is not None else list[EventHandler]()

    def add_handler(self, handler: EventHandler):
        self.handlers.append(handler)

    def manage(self, event: Event):
        for handler in self.handlers:
            if event.type in handler.handles():
                handler.handle(event)


class BasicEventManagerFactory(EventManagerFactory):
    def create(
        self,
        config: bool,
        background_tasks: list[Thread],
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
    ) -> EventManager:
        return BasicEventManager() if config else IgnoreEventManager()
