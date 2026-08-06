from TwitchChannelPointsMiner.classes.events.Transformer import (
    EventTransformer,
    EventTransformerFactory,
)

from TwitchChannelPointsMiner.classes.events.transformers.Strings import (
    AddDateTimeTransformer,
    ColorPaletteTransformer,
    DefaultStringTransformer,
    MultiTransformer,
    StaticStringTransformer,
)
from TwitchChannelPointsMiner.logger import LoggerSettings


class DefaultTransformerFactory(EventTransformerFactory):
    """
    Creates a transformer that turns events into a human-readable string, colorized by a ColorPalette, prepended by the
    date time.
    """

    def create(self, settings: LoggerSettings):
        # First add the timestamp and a separator
        transformers: list[EventTransformer[str]] = [
            AddDateTimeTransformer(
                less=settings.less,
                timezone=settings.time_zone,
            ),
            StaticStringTransformer(" - "),
        ]
        # Then add a colour code if we have a palette
        if settings.color_palette is not None:
            transformers.append(ColorPaletteTransformer(palette=settings.color_palette))
        # Finally add the message
        transformers.append(DefaultStringTransformer())
        return MultiTransformer(*transformers)
