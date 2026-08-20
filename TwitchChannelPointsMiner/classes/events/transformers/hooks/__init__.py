from TwitchChannelPointsMiner.classes.events.Transformer import (
    EventTransformer,
    EventTransformerFactory,
)
from TwitchChannelPointsMiner.classes.events.transformers.Strings import (
    TranslatorNameTransformer,
    TranslatorTransformer,
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

        `"```
        {emoji} {event name}
        {optional "Account: " account_name}
        {message}
        ```"`

        where
        `emoji` is an emoji representative of the event or the miner's default emoji.

        `optional "Account: " account_name` is the user's account name prefixed by "Account: " or nothing

        `message` is a human-readable string representation of the event.
        """
        transformers: list[EventTransformer[str]] = []
        # Add the emoji if enabled
        if settings.emoji:
            transformers.append(EmojiTransformer())
            transformers.append(StaticStringTransformer(value=" "))
        # Then the name of the event plus \n
        transformers.append(TranslatorNameTransformer(translator=settings.translator))
        transformers.append(StaticStringTransformer(value="\n"))
        # Then add account name if set
        transformers.append(
            StaticStringTransformer(
                value=(
                    f"{settings.translator.get_translation().general.account}: {settings.username}\n"
                    if settings.username is not None
                    else ""
                )
            )
        )
        # Add the message
        transformers.append(
            TranslatorTransformer(
                translator=settings.translator, account_username=settings.username
            )
        )
        return CodeblockTransformer(base=MultiTransformer(*transformers))
