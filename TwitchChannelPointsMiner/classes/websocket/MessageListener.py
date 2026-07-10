import abc

from TwitchChannelPointsMiner.classes.entities.Message import Message


class MessageListener(abc.ABC):
    def on_message(self, message: Message):
        """
        Called when a PubSub Message is received.
        :param message: The message received.
        """
        pass
