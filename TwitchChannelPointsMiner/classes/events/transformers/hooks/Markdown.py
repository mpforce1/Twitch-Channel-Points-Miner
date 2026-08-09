from textwrap import dedent
from typing import Literal
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.classes.events.transformers.Strings import (
    DefaultStringTransformer,
)


class CodeblockTransformer(EventTransformer[str]):
    """
    Transformer that puts messages into a code block, e.g.:

    ```text
    An event occurred!
    ```
    """

    def __init__(
        self,
        base: EventTransformer[str] = DefaultStringTransformer(),
        fence: Literal["```", "~~~"] = "```",
        language: str = "",
    ):
        self.base = base
        """The base transformer that produces strings"""
        self.fence = fence
        """The fence characters to use, defaults to ```"""
        self.language = language
        """The language identifier (e.g. "python", "bash", "text", "diff") to use, defaults to no identifier"""

    def transform(self, event: Event) -> str:
        base = dedent(self.base.transform(event)).strip()
        return f"{self.fence}{self.language}\n{base}\n{self.fence}"
