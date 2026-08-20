import abc

from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.logger import LoggerSettings


class EventTransformer[Result](abc.ABC):
    """Transforms Events into a different format."""

    @abc.abstractmethod
    def transform(self, event: Event) -> Result:
        """
        Transforms an Event into a Result.
        :param event: The Event to transform.
        :return: The transformed Result.
        """
        pass


class EventTransformerFactory[Result](abc.ABC):
    @abc.abstractmethod
    def create(self, settings: LoggerSettings, account_username: str) -> EventTransformer[Result]:
        pass
