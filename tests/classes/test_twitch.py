import datetime
from logging import Logger
from unittest.mock import MagicMock, call

import pytest

from TwitchChannelPointsMiner.classes import Twitch
from TwitchChannelPointsMiner.classes.ClientSession import ClientSession
from TwitchChannelPointsMiner.classes.TwitchLogin import TwitchLogin
from TwitchChannelPointsMiner.classes.entities.GiftSub import GiftSub, Target
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.gql.Integration import GQL

test_update_gift_sub_data = [
    # New turbo sub
    (
        Streamer("streamer1", "123456"),
        GiftSub(
            _id="456789",
            target=None,
            gifter=None,
            tier="Turbo",
            display_name="Turbo",
            ends_at=datetime.datetime.fromisoformat("2026-08-20T13:01:00Z"),
        ),
        False,
        None,
        None,
        None,
    ),
    # New tier 1 sub
    (
        Streamer("streamer1", "123456"),
        GiftSub(
            _id="456789",
            target=Target(
                _id="987654", username="targetuser", display_name="TargetUser"
            ),
            gifter=None,
            tier="1",
            display_name="1",
            ends_at=datetime.datetime.fromisoformat("2026-08-20T13:01:00Z"),
        ),
        False,
        None,
        [
            call(
                "[testusername] Tier-1 Gift Sub from Anonymous for TargetUser, ends at 2026-08-20 13:01:00+00:00 (in 31 days)",
                extra={"emoji": ":wrapped_gift:"},
            )
        ],
        None,
    ),
]


@pytest.mark.parametrize(
    "streamer,gift_sub,send_event,account_username,expected_info_log,expected_event",
    test_update_gift_sub_data,
)
def test_update_gift_sub(
    streamer, gift_sub, send_event, account_username, expected_info_log, expected_event
):
    event_manager = MagicMock(spec=EventManager)
    username = "testusername"
    client_session = MagicMock(spec=ClientSession)
    client_session.login = MagicMock(spec=TwitchLogin)
    client_session.login.username = username
    gql = MagicMock(spec=GQL)
    twitch = Twitch.Twitch(
        event_manager=event_manager,
        username=username,
        client_session=client_session,
        gql=gql,
    )

    mock_logger = MagicMock(spec=Logger)

    mock_datetime = MagicMock(spec=datetime.datetime)
    mock_datetime.now.return_value = datetime.datetime.fromisoformat(
        "2026-07-20T13:01:00Z"
    )

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(Twitch, "logger", mock_logger)
        patcher.setattr(datetime, "datetime", mock_datetime)
        twitch.update_gift_sub(
            streamer=streamer,
            gift_sub=gift_sub,
            send_event=send_event,
        )

    if expected_info_log is not None:
        mock_logger.info.assert_has_calls(expected_info_log, True)
    if expected_event is not None:
        event_manager.manage.assert_called_once_with(expected_event)
