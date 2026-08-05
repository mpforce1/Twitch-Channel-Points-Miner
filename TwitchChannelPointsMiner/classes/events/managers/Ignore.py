from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Manager import EventManager


class IgnoreEventManager(EventManager):
    """Event Manager that ignores all events"""

    def manage(self, event: Event):
        pass

    def add_handler(self, handler: EventHandler):
        pass
