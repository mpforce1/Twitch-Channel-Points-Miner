import sys
from unittest.mock import MagicMock
import pytest

from TwitchChannelPointsMiner.classes.EventHook import EventHook
from TwitchChannelPointsMiner.classes.events.Event import StreamUp, StreamerOnline
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.classes.events.handlers.Console import ConsoleHandler
from TwitchChannelPointsMiner.classes.events.handlers.Dispatch import DispatchHandler
from TwitchChannelPointsMiner.classes.events.handlers.Hook import EventHookAdapter
from TwitchChannelPointsMiner.classes.events.handlers.hooks.Discord import (
    add_wait_to_url,
)


def test_console_handler():
    stdout = MagicMock()

    transformer = MagicMock(spec=EventTransformer)
    transformer.transform.return_value = "test message"

    handler = ConsoleHandler(Events.all(), transformer)

    event = MagicMock(spec=StreamerOnline)
    event.type = Events.STREAMER_ONLINE

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(sys, "stdout", stdout)
        handler.handle(event)

    stdout.write.assert_called_once_with("test message\n")


def test_hook_adapter():
    hook = MagicMock(spec=EventHook)

    message = "test message"
    transformer = MagicMock(spec=EventTransformer)
    transformer.transform.return_value = message

    handler = EventHookAdapter(hook=hook, transformer=transformer)

    event = MagicMock(spec=StreamerOnline)
    event_type = Events.STREAMER_ONLINE
    event.type = event_type

    handler.handle(event)

    transformer.transform.assert_called_once_with(event)
    hook.send.assert_called_once_with(message, event_type)


class DispatchHandlerTest(DispatchHandler):
    def __init__(self, handle_stream_up):
        super().__init__()
        self._handle_stream_up = handle_stream_up

    def handles(self) -> Events:
        return Events.all()

    def handle_stream_up(self, event: StreamUp):
        return self._handle_stream_up(event)


def test_dispatch_handler():
    handle_stream_up = MagicMock()
    handler = DispatchHandlerTest(handle_stream_up)

    event = StreamUp(streamer=MagicMock())

    handler.handle(event)

    handle_stream_up.assert_called_once_with(event)


def test_discord_add_wait_to_url():
    assert (
        add_wait_to_url(
            "https://discord.com/api/webhooks/0123456789/0a1B2c3D4e5F6g7H8i9J"
        )
        == "https://discord.com/api/webhooks/0123456789/0a1B2c3D4e5F6g7H8i9J?wait=true"
    )

    assert (
        add_wait_to_url(
            "https://discord.com/api/webhooks/9876543210/78ad737ba0e951cdfbde?wait=true"
        )
        == "https://discord.com/api/webhooks/9876543210/78ad737ba0e951cdfbde?wait=true"
    )

    assert (
        add_wait_to_url(
            "https://discord.com/api/webhooks/9876543210/78ad737ba0e951cdfbde?something=else"
        )
        == "https://discord.com/api/webhooks/9876543210/78ad737ba0e951cdfbde?something=else&wait=true"
    )
