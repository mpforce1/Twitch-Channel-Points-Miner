from TwitchChannelPointsMiner.classes.events.Transformer import (
    EventTransformer,
    EventTransformerFactory,
)
from TwitchChannelPointsMiner.classes.events.transformers.Strings import (
    DefaultStringTransformer,
    EmojiTransformer,
    MultiTransformer,
    StaticStringTransformer,
)
from TwitchChannelPointsMiner.classes.events.transformers.hooks.Markdown import (
    CodeblockTransformer,
)
from TwitchChannelPointsMiner.logger import LoggerSettings


class DefaultEventTransformerFactory(EventTransformerFactory[str]):
    """Creates a Transformer that produces emoji prepended human-readable strings."""

    def create(self, settings: LoggerSettings) -> EventTransformer[str]:
        """
        Creates strings in this format:

        `"```{emoji} {message}```"`

        where
        `emoji` is an emoji representative of the event or the miner's default emoji.

        `message` is a human-readable string representation of the event.
        """
        transformers: list[EventTransformer[str]] = []
        # Add the emoji if enabled
        if settings.emoji:
            transformers.append(EmojiTransformer())
            # Pad right with a space
            transformers.append(StaticStringTransformer(" "))
        # Add the message
        transformers.append(DefaultStringTransformer())
        return CodeblockTransformer(base=MultiTransformer(*transformers))
