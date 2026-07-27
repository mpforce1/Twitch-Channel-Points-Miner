import json
from unittest.mock import MagicMock

from TwitchChannelPointsMiner.classes.PubSub import PubSubHandler
from TwitchChannelPointsMiner.classes.entities.Message import Message
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.websocket.data.UserSubscribeEvents import (
    UserSubscribed,
)


def test_on_message_user_subscribe():
    # Mocks
    parser = MagicMock()
    parsed = UserSubscribed("987654321")
    parser.parse_user_subscribe_events.side_effect = [parsed]
    twitch = MagicMock()
    streamer = Streamer(username="test_user", channel_id="987654321")
    streamers = [streamer]
    events_predictions = dict()
    streamer_system = MagicMock()

    # Args
    message = Message(
        {
            "topic": "user-subscribe-events-v1.123456789",
            "message": json.dumps({"user_id": "123456789", "channel_id": "987654321"}),
        }
    )

    # Object under test
    handler = PubSubHandler(
        streamer_system=streamer_system,
        stream_system=MagicMock(),
        prediction_system=MagicMock(),
        notification_system=MagicMock(),
        parser=parser,
        twitch=twitch,
        streamers=streamers,
        events_predictions=events_predictions,
    )

    # Call object method
    handler.on_message(message)
    streamer_system.subscription.assert_called_once_with(parsed)
