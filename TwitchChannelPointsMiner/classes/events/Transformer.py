import abc

from TwitchChannelPointsMiner.classes.events.Event import Event


class Transformer[Result](abc.ABC):
    """Transforms Events into a different format."""

    @abc.abstractmethod
    def transform(self, event: Event) -> Result:
        """
        Transforms an Event into a Result.
        :param event: The Event to transform.
        :return: The transformed Result.
        """
        pass
