import abc
import io
import os
import pathlib
import random
import traceback
from threading import Lock
from types import TracebackType
from typing import Callable, Literal, TypeAlias, Any

from TwitchChannelPointsMiner.classes.entities.PubsubTopic import PubsubTopic
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.utils.Utils import generate_random_uuid

# To avoid import errors from traceback
_SysExcInfoType: TypeAlias = tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None]


class Anonymiser(abc.ABC):
    """ Anonymises various information from the miner. """

    base_path: str | Literal[False]
    """The beginning part of a filepath to redact. If False, filepaths will not be anonymised."""

    def __init__(
        self,
        channel_ids=True,
        usernames=True,
        channel_points=True,
        strict: bool = False,
        base_path: str | bool = True
    ):
        """
        If `base_path` is True then the expected base directory of this module (the great-grandparent of this file) will
         be used.
        """
        self.anonymise_channel_ids = channel_ids
        """If True, channel ids will be anonymised."""
        self.anonymise_usernames = usernames
        """If True, usernames will be anonymised."""
        self.anonymise_channel_points = channel_points
        """If True, filepaths will be anonymised. This includes filepaths in Exception logs."""
        self.strict = strict
        """If True, the Anonymiser will stop the logging of external data (such as HTTP responses). """
        if base_path is False:
            self.base_path = False
        elif base_path is True:
            self.base_path = str(pathlib.Path(__file__).parent.parent.parent.resolve())
        else:
            self.base_path = base_path

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

    def filepath(self, filepath: str) -> str:
        """
        Redacts the path from the given `filepath` leaving just the filename. Removes either the `base_path` or
        everything before the final separator, if one exists. For example:

        if `self.base_path` = "/home/username/miner"

        and `filename` = "/home/username/miner/module_1/module_2/some_python_file.py"

        then the result path = "[PATH REDACTED]/module_1/module_2/some_python_file.py"

        The main benefit here being that your local username (in this example it's just "username") is redacted.

        However:

        if `filename` = "/home/username/.local/lib/python3.12/site-packages/package/some_python_file.py"

        then the result path = "[PATH REDACTED]/some_python_file.py"

        This is to avoid situations where there might be identifying information in the filepath for a python module
        that the application is using from elsewhere on your system.

        :param filepath: The filename from which to redact the path.
        :return: The redacted filename.
        """
        if self.base_path is False:
            return filepath
        if filepath.startswith(self.base_path):
            index = filepath.index(self.base_path) + len(self.base_path)
            return f"[PATH REDACTED]{filepath[index:]}"
        else:
            try:
                return f"[PATH REDACTED]{filepath[filepath.rindex(os.path.sep):]}"
            except ValueError:
                return filepath

    def format_exception(self, ei: _SysExcInfoType) -> str:
        """
        Formats Exceptions the same as `logging.Formatter` but redacts all filepaths in the exception's stack. This
        applies not just to the current exception but to all chained exceptions recursively (i.e. the Exceptions'
        `__cause__` and `__context__`).

        :param ei: The Exception to format.
        :return: The anonymised exception string.
        """
        # TracebackException can and does explicitly handle None here so type as Any to avoid errors
        exception_type: Any
        exception: Any
        exception_type, exception, exception_traceback = ei
        traceback_exception = traceback.TracebackException(
            exception_type,
            exception,
            exception_traceback,
            limit=None,
            compact=True
        )
        if self.base_path is not False:
            # Redact paths from the current exception and the cause/context iteratively
            current_traceback = traceback_exception
            while current_traceback is not None:
                for frame_summary in current_traceback.stack:
                    frame_summary.filename = self.filepath(frame_summary.filename)
                if current_traceback.__cause__ is not None:
                    current_traceback = current_traceback.__cause__
                elif current_traceback.__context__ is not None:
                    current_traceback = current_traceback.__context__
                else:
                    current_traceback = None

        with io.StringIO() as sio:
            traceback_exception.print(file=sio)
            result = sio.getvalue()
            if result[-1:] == "\n":
                result = result[:-1]
            return result


class Deanonymiser(Anonymiser):
    """ Anonymiser that doesn't change anything. """

    def __init__(self, strict: bool = False):
        super().__init__(channel_ids=False, usernames=False, channel_points=False, strict=strict, base_path=False)

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

    def filepath(self, filepath: str) -> str:
        return filepath


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

    def __init__(
        self,
        channel_ids=True,
        usernames=True,
        channel_points=True,
        strict: bool = True,
        base_path: str | bool = True,
        random_source: RandomSource = RandomSource()
    ):
        super().__init__(channel_ids, usernames, channel_points, strict, base_path)
        self.random_source = random_source

    def channel_id(self, channel_id: str) -> str:
        if self.anonymise_channel_ids:
            return str(self.random_source.random_int(1, 100))
        else:
            return channel_id

    def username(self, username: str) -> str:
        if self.anonymise_usernames:
            return f"Streamer {self.random_source.random_int(1, 100)}"
        else:
            return username

    def channel_points(self, streamer: Streamer) -> int:
        if self.anonymise_channel_points:
            return self.random_source.random_int(0, 1_000_000)
        else:
            return streamer.channel_points

    def hermes_subscription_id(self, _id: str) -> str:
        if self.anonymise_channel_ids:
            return f"Hermes Subscription {self.random_source.random_uuid()}"
        else:
            return _id


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

    def __init__(
        self,
        channel_ids=True,
        usernames=True,
        channel_points=True,
        strict: bool = True,
        base_path: str | bool = True,
        random_points_min: int = 100,
        random_points_max: int = 1_000_000,
        random_source: RandomSource = RandomSource(),
    ):
        super().__init__(channel_ids, usernames, channel_points, strict, base_path)
        self._random_points_min = random_points_min
        self._random_points_max = random_points_max
        self._random_source = random_source

        self._streamer_ids = IncrementingIdStore()
        self._streamer_names = IncrementingIdStore()
        self._streamer_channel_points = dict[str, "ConsistentAnonymiser.ChannelPointsState"]()
        self._hermes_subscription_ids = UUIDStore(random_uuid=random_source.random_uuid)

        self._channel_points_lock = Lock()

    def channel_id(self, channel_id: str) -> str:
        if not self.anonymise_channel_ids:
            return channel_id
        # An empty id means the channel id hasn't been initialised so just return it as is
        if channel_id == "":
            return ""
        return str(self._streamer_ids.id(channel_id))

    def username(self, username: str) -> str:
        if not self.anonymise_usernames:
            return username
        return f"Streamer{self._streamer_names.id(username)}"

    def channel_points(self, streamer: Streamer) -> int:
        if not self.anonymise_channel_points:
            return streamer.channel_points
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
        if self.anonymise_channel_ids:
            return f"Hermes Subscription {self._hermes_subscription_ids.id(subscription_id)}"
        else:
            return subscription_id
