from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Manager import EventManager


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
