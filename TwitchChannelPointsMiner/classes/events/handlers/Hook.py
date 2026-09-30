from TwitchChannelPointsMiner.classes.EventHook import EventHook
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer


class EventHookAdapter(EventHandler):
    """Adapts the newer event pattern onto the older event hook pattern."""

    def __init__(self, hook: EventHook, transformer: EventTransformer[str]):
        self.hook = hook
        self.transformer = transformer

    def handles(self) -> Events:
        return self.hook.events

    def handle(self, event: Event):
        self.hook.send(self.transformer.transform(event), event.type)

