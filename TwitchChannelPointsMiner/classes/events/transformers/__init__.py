from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
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
from TwitchChannelPointsMiner.logger import ColorPalette


class DefaultTransformerFactory(EventTransformerFactory):
    """
    Creates a transformer that turns events into a human-readable string, colorized by a ColorPalette, prepended by the
    date time.
    """

    def __init__(
        self,
        color_palette: ColorPalette | None = ColorPalette(),
        less: bool = False,
        timezone: str | None = None,
    ):
        self.color_palette = color_palette
        """The colour palette to use, if None the default colours will be used"""
        self.less = less
        """Whether to reduce the result size"""
        self.timezone = timezone
        """The timezone in which to render timestamps"""

    def create(self):
        # First add the timestamp and a separator
        transformers: list[EventTransformer[str]] = [
            AddDateTimeTransformer(
                less=self.less,
                timezone=self.timezone,
            ),
            StaticStringTransformer(" - "),
        ]
        # Then add a colour code if we have a palette
        if self.color_palette is not None:
            transformers.append(ColorPaletteTransformer(palette=self.color_palette))
        # Finally add the message
        transformers.append(DefaultStringTransformer())
        return MultiTransformer(*transformers)
