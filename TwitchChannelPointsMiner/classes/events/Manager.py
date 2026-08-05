import abc
from threading import Thread

from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import PredictionEvent
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler


class EventManager(abc.ABC):
    @abc.abstractmethod
    def add_handler(self, handler: EventHandler):
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


class EventManagerFactory(abc.ABC):
    @abc.abstractmethod
    def create(
        self,
        background_tasks: list[Thread],
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
    ) -> EventManager:
        """
        Creates an EventManager.
        :param background_tasks: A list of tasks that can be appended to.
        :param streamers: The list of Streamers managed by the miner.
        :param prediction_events: The Prediction Events managed by the miner.
        """
        pass
