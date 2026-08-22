from threading import Thread
from typing import Protocol, runtime_checkable

from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer


@runtime_checkable
class EventHandlerFactory(Protocol):
    def __call__(
        self, background_tasks: list[Thread], default_transformer: EventTransformer[str], account_name: str
    ) -> EventHandler: ...
