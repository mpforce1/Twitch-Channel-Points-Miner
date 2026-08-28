from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Manager import EventManager


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
