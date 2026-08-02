import datetime
import time
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.events.Event import (
    StreamDown,
    StreamUp,
    StreamViewCount,
)
from TwitchChannelPointsMiner.systems.Streams import StreamSystem


def test_bring_up():
    channel_id = "23796492"
    current_time = 1234567

    streamer = MagicMock()
    streamer.channel_id = channel_id

    event_manager = MagicMock()

    system = StreamSystem(
        twitch=MagicMock(),
        streamers=[streamer],
        event_manager=event_manager,
    )

    timestamp = datetime.datetime.fromtimestamp(123456)
    with pytest.MonkeyPatch.context() as patcher:
        mock_datetime = MagicMock()
        mock_datetime.now = MagicMock()
        mock_datetime.now.return_value = timestamp
        patcher.setattr(datetime, "datetime", mock_datetime)
        patcher.setattr(time, "time", lambda: current_time)
        system.bring_up(channel_id)

    assert streamer.stream_up == current_time
    event_manager.manage.assert_called_once_with(
        StreamUp(timestamp=timestamp, channel_id=channel_id)
    )


def test_bring_down():
    channel_id = "23796492"
    current_time = 1234567

    streamer = MagicMock()
    streamer.channel_id = channel_id

    event_manager = MagicMock()

    system = StreamSystem(
        twitch=MagicMock(),
        streamers=[streamer],
        event_manager=event_manager,
    )

    timestamp = datetime.datetime.fromtimestamp(123456)
    with pytest.MonkeyPatch.context() as patcher:
        mock_datetime = MagicMock()
        mock_datetime.now = MagicMock()
        mock_datetime.now.return_value = timestamp
        patcher.setattr(datetime, "datetime", mock_datetime)
        patcher.setattr(time, "time", current_time)
        system.bring_down(channel_id)

    streamer.set_offline.assert_called_once()
    event_manager.manage.assert_called_once_with(
        StreamDown(timestamp=timestamp, channel_id=channel_id)
    )


@pytest.mark.parametrize("stream_up_elapsed", [False, True])
def test_update_view_count(stream_up_elapsed: bool):
    view_count = 1001

    channel_id = "23796492"

    streamer = MagicMock()
    streamer.channel_id = channel_id
    streamer.stream_up_elapsed.return_value = stream_up_elapsed

    event_manager = MagicMock()

    twitch = MagicMock()

    system = StreamSystem(
        twitch=twitch,
        streamers=[streamer],
        event_manager=event_manager,
    )

    timestamp = datetime.datetime.fromtimestamp(123456)
    with pytest.MonkeyPatch.context() as patcher:
        mock_datetime = MagicMock()
        mock_datetime.now = MagicMock()
        mock_datetime.now.return_value = timestamp
        patcher.setattr(datetime, "datetime", mock_datetime)
        system.update_view_count(channel_id, view_count)

    streamer.stream_up_elapsed.assert_called_once()
    if stream_up_elapsed:
        twitch.check_streamer_online.assert_called_once()
    event_manager.manage.assert_called_once_with(
        StreamViewCount(
            timestamp=timestamp, channel_id=channel_id, view_count=view_count
        )
    )
