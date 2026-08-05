import itertools
from typing import Literal

from colorama import Fore

from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer

rainbow_basic = [
    Fore.RED,
    Fore.YELLOW,
    Fore.GREEN,
    Fore.CYAN,
    Fore.BLUE,
    Fore.MAGENTA,
    Fore.WHITE,
]


def ansi_256(code):
    """
    Creates an 256-colour (8-bit) ansi control sequence.
    :param code: The colour code between 0-256.
    :return: The control sequence.
    """
    return f"\033[38:5:{code}m"


# https://www.hackitu.de/termcolor256/
rainbow_256 = list(
    map(
        ansi_256,
        [
            196,
            202,
            208,
            214,
            220,
            226,
            190,
            154,
            118,
            82,
            46,
            47,
            48,
            49,
            50,
            51,
            45,
            39,
            33,
            27,
            21,
            57,
            93,
            129,
            165,
            201,
            199,
            198,
            197,
        ],
    )
)

Mode = Literal["single"] | Literal["single carryover"] | Literal["multi"]


class _Single:
    def __init__(self, rainbow: list[str], carryover: bool):
        self.rainbow = rainbow
        if carryover:
            # Reuse the same iterator for every line
            iterator = itertools.cycle(rainbow)
            self._get_iterator = lambda: iterator
        else:
            # Create a new iterator for every line
            self._get_iterator = lambda: itertools.cycle(rainbow)

    def apply(self, line: str):
        # zip the iterator and line together, flatten it, then join the result
        return "".join(itertools.chain.from_iterable(zip(self._get_iterator(), line)))


class _Multi:
    def __init__(self, rainbow: list[str]):
        self._iterator = itertools.cycle(rainbow)

    def apply(self, line):
        return f"{self._iterator.__next__()}{line}"


class RainbowTransformer(EventTransformer):
    """Transformer that creates a rainbow effect"""

    def __init__(self, to_str: EventTransformer[str], mode: Mode, rainbow: list[str]):
        self.to_str = to_str
        """The base transformer that turns the Event into a string."""
        self.mode = mode
        """
        If "single" the rainbow will be applied to each character on a single line with no carryover,
        if "single carryover" the rainbow sequence will continue from where it left off on the last line,
        if "multi" the rainbow will be applied to each line.
        """
        self.rainbow = rainbow
        """The list of rainbow colours."""
        if mode == "multi":
            self._state = _Multi(rainbow=rainbow)
        else:
            self._state = _Single(rainbow=rainbow, carryover=mode == "single carryover")

    def transform(self, event: Event) -> str:
        return self._state.apply(self.to_str.transform(event))
