from threading import Thread
from typing import Callable
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


class DelegatingManager(EventManager):
    """Manager that delegates to another manager, can defer adding handlers until a delegate is provided"""

    def __init__(self, manager: EventManager | None = None):
        self.manager = manager
        self._handlers = []

    def set_manager(self, event_manager: EventManager):
        """
        Sets this managers delegate manager and adds any deferred handlers to it.
        :param event_manager: The delegate manager.
        """
        self.manager = event_manager
        for handler in self._handlers:
            self.manager.add_handler(handler)

    def add_handler(self, handler: EventHandler):
        if self.manager is None:
            self._handlers.append(handler)

    def manage(self, event: Event):
        if self.manager is not None:
            self.manager.manage(event)


class DelegatingManagerFactory(EventManagerFactory):
    def __init__(self, get_delegate: Callable[[DelegatingManager], EventManager]):
        self.get_delegate = get_delegate

    def create(
        self,
        background_tasks: list[Thread],
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
    ) -> EventManager:
        manager = DelegatingManager()
        manager.set_manager(self.get_delegate(manager))
        return manager
