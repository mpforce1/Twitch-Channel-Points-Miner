import abc
import random
from threading import Lock
from typing import Callable

from TwitchChannelPointsMiner.classes.entities.PubsubTopic import PubsubTopic
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.utils.Utils import generate_random_uuid


class Anonymiser(abc.ABC):
    """ Anonymises various information from the miner. """

    @abc.abstractmethod
    def channel_id(self, channel_id: str) -> str:
        """
        Gets a channel id for the given Streamer channel id.

        :param channel_id: The id of the Streamer.
        :return: The id.
        """
        pass

    @abc.abstractmethod
    def username(self, username: str) -> str:
        """
        Gets a username for the Streamer with the given username.

        :param username: The username of the Streamer.
        :return: The username.
        """
        pass

    @abc.abstractmethod
    def channel_points(self, streamer: Streamer) -> int:
        """
        Gets the channel points for the given Streamer.

        :param streamer: The Streamer.
        :return: The channel points.
        """
        pass

    @abc.abstractmethod
    def hermes_subscription_id(self, _id: str) -> str:
        """
        Gets a Hermes topic subscription id.

        :param _id: The id to anonymise.
        :return: The anonymised id.
        """
        pass

    def streamer_username(self, streamer: Streamer) -> str:
        """
        Gets a name for the given Streamer.

        :param streamer: The Streamer.
        :return: The name.
        """
        return self.username(streamer.username)

    def streamer_channel_id(self, streamer: Streamer) -> str:
        """
        Gets a channel id for the given Streamer.

        :param streamer: The Streamer.
        :return: The id.
        """
        return self.channel_id(streamer.channel_id)

    def topic(self, topic: str | PubsubTopic) -> str:
        """
        Redacts channel id in the given topic string ("[topic name].[channel id]") or PubsubTopic object.

        :param topic: The topic.
        :return: The redacted topic string.
        """
        topic_str = str(topic)
        topic, _id = topic_str.split(".")
        return f"{topic}.{self.channel_id(_id)}"


class Deanonymiser(Anonymiser):
    """ Anonymiser that doesn't change anything. """

    def channel_id(self, channel_id: str) -> str:
        return channel_id

    def username(self, username: str) -> str:
        return username

    def channel_points(self, streamer: Streamer) -> int:
        return streamer.channel_points

    def topic(self, topic: str | PubsubTopic) -> str:
        return str(topic)

    def hermes_subscription_id(self, _id: str) -> str:
        return _id


class RandomSource:
    """Utility to allow overriding random behaviour."""

    def __init__(self, random_int=random.randint, random_uuid=generate_random_uuid):
        self._random_int: Callable[[int, int], int] = random_int
        self._random_uuid: Callable[[], str] = random_uuid

    def random_int(self, a: int, b: int) -> int:
        return self._random_int(a, b)

    def random_uuid(self):
        return self._random_uuid()


class RandomAnonymiser(Anonymiser):
    """ Anonymises various information from the miner in an inconsistent (random) manner. """

    def __init__(self, random_source: RandomSource):
        self.random_source = random_source

    def channel_id(self, channel_id: str) -> str:
        return str(self.random_source.random_int(1, 100))

    def username(self, username: str) -> str:
        return f"Streamer {self.random_source.random_int(1, 100)}"

    def channel_points(self, streamer: Streamer) -> int:
        return self.random_source.random_int(0, 1_000_000)

    def hermes_subscription_id(self, _id: str) -> str:
        return f"Hermes Subscription {self.random_source.random_uuid()}"


class IdStore[ValueType](abc.ABC):
    """ Base class to help store a map of keys to ids. """

    def __init__(self):
        self._ids = dict[str, ValueType]()
        self._lock = Lock()

    @abc.abstractmethod
    def _next_id(self) -> ValueType:
        pass

    def id(self, key: str):
        """
        Gets the id for the given key, this will either be the previous id generated for the given key or a new id if
        this is the first usage.

        :param key: The key for which to get the id.
        :return: The id generated/retrieved.
        """
        with self._lock:
            if key not in self._ids:
                self._ids[key] = self._next_id()
            return self._ids[key]


class UUIDStore(IdStore[str]):
    """Utility top help store a map of keys to random UUIDs."""

    def __init__(self, random_uuid=generate_random_uuid):
        super().__init__()
        self.random_uuid = random_uuid

    def _next_id(self) -> str:
        return self.random_uuid()


class IncrementingIdStore(IdStore[int]):
    """ Utility to help store a map of keys to an incrementing id/index. """

    def __init__(self):
        super().__init__()
        self._last_id = 0

    def _next_id(self) -> int:
        self._last_id += 1
        return self._last_id


class ConsistentAnonymiser(Anonymiser):
    """ Anonymises various information from the miner in a consistent manner. """

    class ChannelPointsState:
        def __init__(self, fake_points: int, last_real_points: int):
            self.fake_points = fake_points
            self.last_real_points = last_real_points

    def __init__(self, random_points_min: int = 100, random_points_max: int = 1_000_000, random_source=RandomSource()):
        self._random_points_min = random_points_min
        self._random_points_max = random_points_max
        self._random_source = random_source

        self._streamer_ids = IncrementingIdStore()
        self._streamer_names = IncrementingIdStore()
        self._streamer_channel_points = dict[str, "ConsistentAnonymiser.ChannelPointsState"]()
        self._hermes_subscription_ids = UUIDStore(random_uuid=random_source.random_uuid)

        self._channel_points_lock = Lock()

    def channel_id(self, channel_id: str) -> str:
        # An empty id means the channel id hasn't been initialised so just return it as is
        if channel_id == "":
            return ""
        return str(self._streamer_ids.id(channel_id))

    def username(self, username: str) -> str:
        return f"Streamer{self._streamer_names.id(username)}"

    def channel_points(self, streamer: Streamer) -> int:
        with self._channel_points_lock:
            if streamer.username not in self._streamer_channel_points:
                state = ConsistentAnonymiser.ChannelPointsState(
                    fake_points=self._random_source.random_int(self._random_points_min, self._random_points_max),
                    last_real_points=streamer.channel_points
                )
                self._streamer_channel_points[streamer.username] = state
            else:
                state = self._streamer_channel_points[streamer.username]
                delta = streamer.channel_points - state.last_real_points
                state.fake_points += delta
                state.last_real_points = streamer.channel_points
        return state.fake_points

    def hermes_subscription_id(self, subscription_id: str) -> str:
        return f"Hermes Subscription {self._hermes_subscription_ids.id(subscription_id)}"
