import logging

from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Manager import EventManager

logger = logging.getLogger(__name__)


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
        else:
            self.manager.add_handler(handler)

    def manage(self, event: Event):
        if self.manager is not None:
            self.manager.manage(event)
        else:
            logger.warning(
                f"Delegating Manager cannot manage event, a delegate hasn't yet been set: {type(event).__name__}"
            )
