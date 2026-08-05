from enum import Enum, auto, StrEnum

# import Events to act as a drop in replacement for the old Event enum
from TwitchChannelPointsMiner.classes.events.Events import Events  # pyright: ignore


class Priority(Enum):
    ORDER = auto()
    STREAK = auto()
    DROPS = auto()
    SUBSCRIBED = auto()
    POINTS_ASCENDING = auto()
    POINTS_DESCENDING = auto()
    WATCH_SESSION = auto()
    WEEKLY_REWARDS = auto()  #


class StreamerSource(StrEnum):
    """Represents the source of a Streamer."""

    Streamers = "streamers"
    """ The streamer came from the streamers list """
    Followers = "followers"
    """ The streamer came from the followers list """


class FollowersOrder(Enum):
    ASC = auto()
    DESC = auto()

    def __str__(self):
        return self.name


# Empty object shared between class
class Settings(object):
    __slots__ = [
        "logger",
        "streamer_settings",
        "enable_analytics",
        "disable_ssl_cert_verification",
        "disable_at_in_nickname",
        "use_hermes",
    ]

    def __str__(self):
        return self.name

    @classmethod
    def get(cls, key):
        return getattr(cls, str(key)) if str(key) in dir(cls) else None
