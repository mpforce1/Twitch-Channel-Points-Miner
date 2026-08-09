import abc

from TwitchChannelPointsMiner.classes.events.Event import (
    Event,
)
from TwitchChannelPointsMiner.classes.events.Events import Events


class EventHandler(abc.ABC):
    @abc.abstractmethod
    def handles(self) -> Events:
        """Returns a union of the Events this Handler can handle."""
        pass

    @abc.abstractmethod
    def handle(self, event: Event):
        """
        Handles the given Event.
        :param event: The event to handle.
        """
        pass
