from TwitchChannelPointsMiner.classes.events.Transformer import (
    EventTransformer,
    EventTransformerFactory,
)

from TwitchChannelPointsMiner.classes.events.transformers.Strings import (
    EmojiTransformer,
    LineConfig,
    TimestampTransformer,
    ColorPaletteTransformer,
    TranslatorTransformer,
    MultiTransformer,
    StaticStringTransformer,
    TruncateTransformer,
)
from TwitchChannelPointsMiner.logger import LoggerSettings


class DefaultTransformerFactory(EventTransformerFactory):
    """
    Creates a transformer that turns events into a human-readable string, colorized by a ColorPalette, prepended by an
    emoji and the event's date time.
    """

    def create(self, settings: LoggerSettings):
        """
        Creates strings in this format:

        `"{timestamp} - {colour code}{emoji}  {message}"`

        where

        `timestamp` is formatted as either `"{d/%m/%y %H:%M:%S}` or {"%d/%m %H:%M:%S"} depending on `settings.less`.

        `colour code` is a 0-width ansi colour code.

        `emoji` is an emoji representative of the event or the miner's default emoji.

        `message` is a human-readable string representation of the event.
        """
        # First add the timestamp and a separator
        transformers: list[EventTransformer[str]] = [
            TimestampTransformer(
                less=settings.less,
                timezone=settings.time_zone,
            ),
            StaticStringTransformer(" - "),
        ]
        # Then add account name if set
        if settings.username is not None:
            transformers.append(
                StaticStringTransformer(value=f"{settings.username} - ")
            )
        # Then add a colour code if we have a palette
        if settings.color_palette is not None:
            transformers.append(ColorPaletteTransformer(palette=settings.color_palette))
        # Add the emoji if enabled
        if settings.emoji:
            transformers.append(EmojiTransformer())
            # Pad right with 2 spaces
            transformers.append(StaticStringTransformer("  "))
        # Add the message
        transformers.append(TranslatorTransformer(translator=settings.translator))
        line_transformer = MultiTransformer(*transformers)
        # Optionally truncate the line
        if settings.console_truncate is not False:
            return TruncateTransformer(
                base=line_transformer,
                default=LineConfig(max_length=settings.console_truncate),
            )
        else:
            return line_transformer
