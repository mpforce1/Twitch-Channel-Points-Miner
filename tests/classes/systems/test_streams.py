import datetime
import time
from unittest.mock import MagicMock, call

import pytest

from TwitchChannelPointsMiner.classes.Anonymiser import Deanonymiser
from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    Streamer,
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.events.Event import (
    StreamDown,
    StreamUp,
    StreamViewCount,
    StreamerOffline,
)
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropsCampaign,
    DropsProgressCriteria,
    DropsReward,
    DropsRewardGroup,
    DropsRewardGroupSelfEdge,
    DropsUnlockRequirement,
)
from TwitchChannelPointsMiner.classes.systems.Streams import StreamSystem
from TwitchChannelPointsMiner.logger import LoggerSettings


def test_bring_up():
    channel_id = "23796492"
    current_time = 1234567

    streamer = MagicMock()
    streamer.channel_id = channel_id

    event_manager = MagicMock()

    system = StreamSystem(
        twitch=MagicMock(),
        streamers=[streamer],
        campaigns={},
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
        StreamUp(timestamp=timestamp, streamer=streamer)
    )


def test_bring_down():
    channel_id = "23796492"
    current_time = 1234567

    streamer = MagicMock()
    streamer.channel_id = channel_id
    streamer.is_online = True

    event_manager = MagicMock()

    system = StreamSystem(
        twitch=MagicMock(),
        streamers=[streamer],
        campaigns={},
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
    event_manager.manage.assert_has_calls(
        [
            call(StreamDown(timestamp=timestamp, streamer=streamer)),
            call(StreamerOffline(timestamp=timestamp, streamer=streamer)),
        ]
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
        campaigns={},
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
        StreamViewCount(timestamp=timestamp, streamer=streamer, view_count=view_count)
    )


test_update_campaigns_data = [
    # No campaigns
    (
        Streamer(
            "12345",
            "12345",
            settings=StreamerSettings(claim_drops=True),
            is_online=True,
        ),
        datetime.datetime.fromisoformat("2026-10-17T18:00:00Z"),
        [],
        [],
    ),
    # No progressable campaigns
    (
        Streamer(
            "12345",
            "12345",
            settings=StreamerSettings(claim_drops=True),
            is_online=True,
        ),
        datetime.datetime.fromisoformat("2026-10-17T18:00:00Z"),
        [
            # No drops
            DropsCampaign(
                id="01a14adc-f2f1-70c1-8772-1265b8b70839",
                name="test drop campaign",
                start_at=datetime.datetime.fromisoformat("2026-10-17T18:00:00Z"),
                end_at=datetime.datetime.fromisoformat("2026-10-18T18:00:00Z"),
                game=None,
                reward_groups=[],
            ),
            # Drop watch requirement already completed
            DropsCampaign(
                id="01a14ae1-5610-74ed-b8a4-9733e49067cb",
                name="test drop campaign 2",
                start_at=datetime.datetime.fromisoformat("2026-10-17T18:00:00Z"),
                end_at=datetime.datetime.fromisoformat("2026-10-18T18:00:00Z"),
                game=None,
                reward_groups=[
                    DropsRewardGroup(
                        id="01a14ae1-c8b9-743d-829d-e57cfa2fdd1d",
                        name="test reward group",
                        track=None,
                        lane=None,
                        progress_criteria=DropsProgressCriteria(
                            requirement_type="minutes_watched",
                            requirements=DropsUnlockRequirement(
                                minutes_watched=100,
                                subs=0,
                                turbo_subs=0,
                            ),
                            categories=[],
                            repeatable_config=None,
                        ),
                        rewards=[],
                        self_edge=DropsRewardGroupSelfEdge(
                            status="IN_PROGRESS",
                            current_minutes_watched=100,
                            current_subs=0,
                            grant_count=1,
                            current_window=None,
                        ),
                    )
                ],
            ),
        ],
        [
            "01a14adc-f2f1-70c1-8772-1265b8b70839",
            "01a14ae1-5610-74ed-b8a4-9733e49067cb",
        ],
    ),
    # Progressible campaigns
    (
        Streamer(
            "12345",
            "12345",
            settings=StreamerSettings(claim_drops=True),
            is_online=True,
        ),
        datetime.datetime.fromisoformat("2026-10-17T18:00:00Z"),
        [
            DropsCampaign(
                id="01a14ae5-6252-72a0-82bc-7e8f272cc2c0",
                name="test drop campaign",
                start_at=datetime.datetime.fromisoformat("2026-10-17T18:00:00Z"),
                end_at=datetime.datetime.fromisoformat("2026-10-18T18:00:00Z"),
                game=None,
                reward_groups=[
                    DropsRewardGroup(
                        id="01a14ae5-8638-72ae-a726-892afe08f11f",
                        name="test reward group",
                        track=None,
                        lane=None,
                        progress_criteria=DropsProgressCriteria(
                            requirement_type="minutes_watched",
                            requirements=DropsUnlockRequirement(
                                minutes_watched=100,
                                subs=0,
                                turbo_subs=0,
                            ),
                            categories=[],
                            repeatable_config=None,
                        ),
                        rewards=[
                            DropsReward(
                                id="01a14aeb-4962-742c-adc1-9be8d562bc3e",
                                name="test reward",
                                is_account_connected=True,
                                account_link_url="",
                            )
                        ],
                        self_edge=DropsRewardGroupSelfEdge(
                            status="IN_PROGRESS",
                            current_minutes_watched=10,
                            current_subs=0,
                            grant_count=0,
                            current_window=None,
                        ),
                    )
                ],
            ),
        ],
        ["01a14ae5-6252-72a0-82bc-7e8f272cc2c0"],
    ),
]
Settings.logger = LoggerSettings(anonymiser=Deanonymiser())


@pytest.mark.parametrize(
    "streamer,time_now,campaigns,expected_ids", test_update_campaigns_data
)
def test_update_campaigns(
    streamer: Streamer,
    time_now: datetime.datetime,
    campaigns: list[DropsCampaign],
    expected_ids: list[str],
):
    event_manager = MagicMock()

    twitch = MagicMock()
    campaign_store = dict()

    system = StreamSystem(
        twitch=twitch,
        streamers=[streamer],
        campaigns=campaign_store,
        event_manager=event_manager,
    )
    system._fetch_progress = MagicMock()
    system._fetch_progress.return_value = campaigns

    with pytest.MonkeyPatch.context() as patcher:
        mock_datetime = MagicMock()
        mock_datetime.now = MagicMock()
        mock_datetime.now.return_value = time_now
        patcher.setattr(datetime, "datetime", mock_datetime)
        system.update_campaigns(streamer.channel_id)

    assert len(streamer.stream.campaigns) == len(expected_ids)
    for item in streamer.stream.campaigns:
        assert item in expected_ids
    for item in expected_ids:
        assert item in streamer.stream.campaigns

    for campaign in campaigns:
        assert campaign.id in campaign_store
