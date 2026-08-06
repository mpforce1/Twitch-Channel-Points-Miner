from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Handler import (
    EventHandler,
    EventHandlerFactory,
)


class IgnoreEventHandler(EventHandler):
    """Event Handler that ignores all events"""

    def handles(self) -> Events:
        return Events.none()

    def handle(self, event: Event):
        return


class IgnoreEventHandlerFactory(EventHandlerFactory):
    def create(self) -> IgnoreEventHandler:
        return IgnoreEventHandler()
