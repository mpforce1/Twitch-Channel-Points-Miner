import datetime
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.transformers.Strings import (
    AddDateTimeTransformer,
    ColorPaletteTransformer,
    prepend_emoji,
)


def test_prepend_emoji():
    assert (
        prepend_emoji(message="test message", emoji=":partying_face:")
        == "🥳  test message"
    )
    assert (
        prepend_emoji(message="another test message", emoji=None)
        == "another test message"
    )


test_add_date_time_data = [
    (
        False,
        None,
        "test message",
        datetime.datetime.fromisoformat("2026-08-04T09:00:00Z"),
        "04/08/26 09:00:00",
    ),
    (
        False,
        "utc",
        "test message",
        datetime.datetime.fromisoformat("2026-08-04T09:00:00Z"),
        "04/08/26 09:00:00",
    ),
    (
        False,
        "US/Hawaii",
        "test message",
        datetime.datetime.fromisoformat("2026-08-04T09:00:00"),
        "03/08/26 23:00:00",
    ),
    (
        True,
        None,
        "test message",
        datetime.datetime.fromisoformat("2026-08-04T09:00:00"),
        "04/08 09:00:00",
    ),
    (
        True,
        "utc",
        "test message",
        datetime.datetime.fromisoformat("2026-08-04T09:00:00Z"),
        "04/08 09:00:00",
    ),
    (
        True,
        "US/Hawaii",
        "test message",
        datetime.datetime.fromisoformat("2026-08-04T09:00:00"),
        "03/08 23:00:00",
    ),
]


@pytest.mark.parametrize(
    "less,timezone,base_message,timestamp,expected", test_add_date_time_data
)
def test_add_date_time_transformer(less, timezone, base_message, timestamp, expected):
    transformer = AddDateTimeTransformer(less=less, timezone=timezone)
    event = MagicMock()
    event.timestamp = timestamp
    assert transformer.transform(event) == expected


def test_color_palette_transformer():
    palette = MagicMock()
    event_type = Events.STREAMER_ONLINE
    transformer = ColorPaletteTransformer(palette=palette)
    event = MagicMock()
    event.type = event_type
    transformer.transform(event)
    palette.get.assert_called_once_with(event_type.name)
