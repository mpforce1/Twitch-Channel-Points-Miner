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
    parser.parse_user_subscribe_events.side_effect = [UserSubscribed("987654321")]
    twitch = MagicMock()
    streamer = Streamer(username="test_user", channel_id="987654321")
    streamers = [streamer]
    events_predictions = dict()

    # Args
    message = Message(
        {
            "topic": "user-subscribe-events-v1.123456789",
            "message": json.dumps({"user_id": "123456789", "channel_id": "987654321"}),
        }
    )

    # Object under test
    handler = PubSubHandler(
        parser=parser,
        twitch=twitch,
        streamers=streamers,
        events_predictions=events_predictions,
    )

    # Call object method
    handler.on_message(message)
    twitch.check_gift_sub.assert_called_once_with(streamer)
