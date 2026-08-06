import abc

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.PubsubTopic import PubsubTopic
from TwitchChannelPointsMiner.classes.websocket.MessageListener import MessageListener


class WebSocketPool(abc.ABC):
    """Abstract base class for a WebSocket pool that allows submitting PubsubTopics."""

    @abc.abstractmethod
    def start(self):
        """Starts the WebSocket Pool."""
        raise NotImplementedError()

    @abc.abstractmethod
    def end(self):
        """Ends the WebSocket Pool."""
        raise NotImplementedError()

    @abc.abstractmethod
    def add_listener(self, listener: MessageListener):
        """
        Adds a listener to this pool
        :param listener: The listener to add
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def submit(self, topic: PubsubTopic):
        """
        Submits the given topic to an available client.
        :param topic: The topic to submit.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def check_stale_connections(self):
        """Finds any stale clients, i.e. no recent ping, and reconnects them."""
        raise NotImplementedError()


class WebSocketPoolFactory(abc.ABC):
    @abc.abstractmethod
    def create(self, twitch: Twitch, use_hermes: bool) -> WebSocketPool:
        pass
