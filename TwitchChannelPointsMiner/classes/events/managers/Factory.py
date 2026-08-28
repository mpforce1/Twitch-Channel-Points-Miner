import abc
from dataclasses import dataclass
from threading import Thread
from typing import Literal

from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.events.managers.Queue import QueueConfiguration
from TwitchChannelPointsMiner.logger import LoggerSettings


@dataclass(kw_only=True)
class EventManagerConfiguration:
    console: bool = False
    queue: QueueConfiguration | None = None
    events: Events | list[Events] = Events.all()


class EventManagerFactory(abc.ABC):
    @abc.abstractmethod
    def create(
        self,
        config: EventManagerConfiguration | Literal[True] | None,
        settings: LoggerSettings,
        account_username: str,
        background_tasks: list[Thread],
    ) -> EventManager:
        """
        Creates an EventManager.
        :param config: If not None, an EventManager will be created, otherwise Events will be ignored.
        :param settings: The logger settings for the application.
        :param background_tasks: A list of tasks that can be appended to.
        :param account_username: The username of the account running the miner.
        """
        pass
