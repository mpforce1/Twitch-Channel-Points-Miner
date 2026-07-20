import abc
from threading import Thread

from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import Handler


class EventManager(Thread, abc.ABC):
    @abc.abstractmethod
    def add_handler(self, handler: Handler):
        """
        Adds an Event Handler to this Manager.
        :param handler: The Handler to add.
        """
        pass

    @abc.abstractmethod
    def manage(self, event: Event):
        """
        Manages the given Event by submitting it to registered Event Handlers.
        :param event: The Event to manage.
        """
        pass

