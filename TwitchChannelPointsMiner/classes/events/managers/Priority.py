from threading import Thread
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import PredictionEvent
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Manager import (
    EventManager,
    EventManagerFactory,
)


class PriorityManager(EventManager):
    """Manager that first manages events via the priority handler, then the delegate manager."""

    def __init__(self, delegate_manager: EventManager):
        self.priority_handler = None
        self.delegate_manager = delegate_manager

    def set_priority_handler(self, handler: EventHandler):
        self.priority_handler = handler

    def add_handler(self, handler: EventHandler):
        self.delegate_manager.add_handler(handler)

    def manage(self, event: Event):
        if (
            self.priority_handler is not None
            and event.type in self.priority_handler.handles()
        ):
            self.priority_handler.handle(event)
        self.delegate_manager.manage(event)


class PriorityManagerFactory(EventManagerFactory):
    def __init__(self, delegate_manager: EventManager):
        self.delegate_manager = delegate_manager

    def create(
        self,
        background_tasks: list[Thread],
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
    ) -> PriorityManager:
        return PriorityManager(self.delegate_manager)
