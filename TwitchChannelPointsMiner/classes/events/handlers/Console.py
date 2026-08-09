import sys

from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer


class ConsoleHandler(EventHandler):
    """Handler that prints to stdout"""

    def __init__(self, events: Events, transformer: EventTransformer[str]):
        self.events = events
        self.transformer = transformer

    def handle(self, event: Event):
        sys.stdout.write(f"{self.transformer.transform(event)}\n")

    def handles(self) -> Events:
        return self.events
