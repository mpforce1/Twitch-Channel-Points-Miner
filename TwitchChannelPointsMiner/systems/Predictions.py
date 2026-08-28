import abc
import logging

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.websocket.data import (
    PredictionsChannel,
    PredictionsUser,
)

logger = logging.getLogger(__name__)


class Predictor(abc.ABC):
    """Uses information about Prediction Events to make predictions on them"""

    @abc.abstractmethod
    def event_created(self, event: PredictionEvent):
        """
        A new event has been created.
        :param event: The event.
        """
        pass

    @abc.abstractmethod
    def event_updated(self, event: PredictionEvent):
        """
        An existing event has been updated.
        :param event:
        """
        pass

    @abc.abstractmethod
    def make_prediction(self, event_id: str):
        """
        Create a prediction for the Event with the given id.
        :param event_id: The id of the event on which to predict.
        """
        pass


class PredictionSystem(abc.ABC):
    """System that handles Twitch Prediction Events"""

    @abc.abstractmethod
    def event_created(self, data: PredictionsChannel.EventCreated):
        """
        A new Prediction Event has been created.
        :param data: The data for the event.
        """
        pass

    @abc.abstractmethod
    def event_updated(self, data: PredictionsChannel.EventUpdated):
        """
        An existing Prediction Event has been updated.
        :param data: The data for the event update.
        """
        pass

    @abc.abstractmethod
    def user_prediction_made(self, data: PredictionsUser.PredictionMade):
        """
        The current user has made a prediction on a prediction event.
        :param data: The data for the prediction.
        """
        pass

    @abc.abstractmethod
    def user_prediction_result(self, data: PredictionsUser.PredictionResult):
        """
        A Prediction for the current user has resulted.
        :param data: The data for the result.
        """
        pass


class PredictorFactory(abc.ABC):
    """Factory that produces Predictors"""

    @abc.abstractmethod
    def create(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
        event_manager: EventManager,
    ) -> Predictor:
        pass


class PredictionSystemFactory(abc.ABC):
    """Factory that produces Prediction Systems"""

    @abc.abstractmethod
    def create(
        self,
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
        event_manager: EventManager,
        predictor: Predictor,
    ) -> PredictionSystem:
        """
        Creates a new PredictionSystem.
        :return:
        """
        pass
