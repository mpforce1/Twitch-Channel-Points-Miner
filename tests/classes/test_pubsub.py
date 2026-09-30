from typing import get_args
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes import PubSub
from TwitchChannelPointsMiner.classes.PubSub import PubSubHandler
from TwitchChannelPointsMiner.classes.websocket.data.Model import Model


class InvalidDataType:
    pass


def test_handles_all_data_types():
    parser = MagicMock()
    logger = MagicMock()

    pubsub = PubSubHandler(
        streamer_system=MagicMock(),
        stream_system=MagicMock(),
        prediction_system=MagicMock(),
        notification_system=MagicMock(),
        parser=parser,
    )

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(PubSub, "logger", logger)
        for data_type in get_args(Model):
            # Dynamically create subtypes for every Model type
            dummy_event = MagicMock(spec=data_type)
            dummy_event.id = ""
            dummy_event.viewers = 1

            parser.message_parser.return_value = dummy_event

            # Should never throw an Exception
            pubsub.on_message(MagicMock())
        # Check error output
        logger.error.assert_not_called()

        # Test for an unknown type
        parser.message_parser.return_value = InvalidDataType()
        pubsub.on_message(MagicMock())
        logger.error.assert_called_once()
