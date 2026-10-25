import datetime
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropsError,
    DropsPageClaimDropsResponse,
)
from TwitchChannelPointsMiner.classes.systems.Drops import DropsSystem
from TwitchChannelPointsMiner.classes.websocket.data.UserDropEvents import DropProgress

test_refresh_inventory_data = [
    (
        datetime.datetime.fromisoformat("2026-10-17T16:50:00"),
        datetime.datetime.fromisoformat("2026-10-17T16:50:00"),
        datetime.timedelta(minutes=10),
        False,
    ),
    (
        datetime.datetime.fromisoformat("2026-10-17T17:00:00"),
        datetime.datetime.fromisoformat("2026-10-17T16:50:00"),
        datetime.timedelta(minutes=10),
        False,
    ),
    (
        datetime.datetime.fromisoformat("2026-10-17T17:00:01"),
        datetime.datetime.fromisoformat("2026-10-17T16:50:00"),
        datetime.timedelta(minutes=10),
        True,
    ),
    (
        datetime.datetime.fromisoformat("2026-10-17T17:50:00"),
        datetime.datetime.fromisoformat("2026-10-17T16:50:00"),
        datetime.timedelta(minutes=10),
        True,
    ),
]


@pytest.mark.parametrize(
    "now,inventory_updated,threshold,expected", test_refresh_inventory_data
)
def test_refresh_inventory(
    now,
    inventory_updated: datetime.datetime,
    threshold: datetime.timedelta,
    expected: bool,
):
    streamers = []
    campaigns = {}
    twitch = MagicMock()
    event_manager = MagicMock()
    system = DropsSystem(
        streamers=streamers,
        campaigns=campaigns,
        twitch=twitch,
        event_manager=event_manager,
    )
    system.inventory_updated = inventory_updated
    system.inventory_update_threshold = threshold

    new_inventory = MagicMock()
    twitch.gql = MagicMock()
    twitch.gql.get_inventory.return_value = new_inventory

    with pytest.MonkeyPatch.context() as patcher:
        # Setup datetime.now patch
        mock_datetime = MagicMock()
        mock_datetime.now = MagicMock()
        mock_datetime.now.return_value = now
        patcher.setattr(datetime, "datetime", mock_datetime)

        # Call method
        system._refresh_inventory()

        # Check result
        if expected:
            twitch.gql.get_inventory.assert_called_once()
            assert system.inventory_updated == now
        else:
            twitch.gql.get_inventory.assert_not_called()
            assert system.inventory_updated is not now


test_claim_drop_data = [
    (None, None, False),
    ("1234", DropsPageClaimDropsResponse(None, None), False),
    ("1234", DropsPageClaimDropsResponse("OTHER_STATUS", None), False),
    ("1234", DropsPageClaimDropsResponse("ELIGIBLE_FOR_ALL", None), True),
    ("1234", DropsPageClaimDropsResponse("DROP_INSTANCE_ALREADY_CLAIMED", None), True),
    (
        "1234",
        DropsPageClaimDropsResponse(
            "CLAIMABLE",
            DropsError(
                "unlinked",
                "you must link your account",
            ),
        ),
        False,
    ),
]


@pytest.mark.parametrize("instance_id,response,expected", test_claim_drop_data)
def test_claim_drop(instance_id: str, response, expected: bool):
    streamers = []
    campaigns = dict()
    twitch = MagicMock()
    event_manager = MagicMock()
    system = DropsSystem(
        streamers=streamers,
        campaigns=campaigns,
        twitch=twitch,
        event_manager=event_manager,
    )

    twitch.gql = MagicMock()
    twitch.gql.claim_drop_rewards.return_value = response

    drop = MagicMock()
    drop.drop_instance_id = instance_id

    result = system.claim_drop(drop)

    if expected:
        twitch.gql.claim_drop_rewards.assert_called_once()
    assert result == expected


test_claim_all_drops_data = [
    # No campaigns
    (dict(), 0),
    # No valid campaigns
    (
        {
            # Not connected
            "1234": Campaign(
                _id="1234",
                name="campaign1",
                game=None,
                status="",
                end_at=datetime.datetime.now(datetime.timezone.utc),
                start_at=datetime.datetime.now(datetime.timezone.utc),
                is_account_connected=False,
                account_link_url=None,
                drops=[],
            ),
            # No drops
            "2345": Campaign(
                _id="2345",
                name="campaign2",
                game=None,
                status="",
                end_at=datetime.datetime.now(datetime.timezone.utc),
                start_at=datetime.datetime.now(datetime.timezone.utc),
                is_account_connected=True,
                account_link_url="https://example.com/",
                drops=[],
            ),
            # Already claimed
            "3456": Campaign(
                _id="3456",
                name="campaign3",
                game=None,
                status="",
                end_at=datetime.datetime.now(datetime.timezone.utc),
                start_at=datetime.datetime.now(datetime.timezone.utc),
                is_account_connected=True,
                account_link_url="https://example.com/",
                drops=[
                    Drop(
                        _id="1234",
                        name="test drop name",
                        end_at=MagicMock(),
                        start_at=MagicMock(),
                        benefits=[],
                        minutes_required=0,
                        subs_required=0,
                        current_minutes_watched=0,
                        current_subs=0,
                        drop_instance_id="1234",
                        is_claimed=True,
                    )
                ],
            ),
            # No drop instance id
            "4567": Campaign(
                _id="4567",
                name="campaign4",
                game=None,
                status="",
                end_at=datetime.datetime.now(datetime.timezone.utc),
                start_at=datetime.datetime.now(datetime.timezone.utc),
                is_account_connected=True,
                account_link_url="https://example.com/",
                drops=[
                    Drop(
                        _id="1234",
                        name="test drop name",
                        end_at=MagicMock(),
                        start_at=MagicMock(),
                        benefits=[],
                        minutes_required=0,
                        subs_required=0,
                        current_minutes_watched=0,
                        current_subs=0,
                        drop_instance_id=None,
                        is_claimed=False,
                    )
                ],
            ),
        },
        0,
    ),
    # Some valid
    (
        {
            # Already claimed
            "3456": Campaign(
                _id="3456",
                name="campaign1",
                game=None,
                status="",
                end_at=datetime.datetime.now(datetime.timezone.utc),
                start_at=datetime.datetime.now(datetime.timezone.utc),
                is_account_connected=True,
                account_link_url="https://example.com/",
                drops=[
                    Drop(
                        _id="1234",
                        name="test drop name",
                        end_at=MagicMock(),
                        start_at=MagicMock(),
                        benefits=[],
                        minutes_required=0,
                        subs_required=0,
                        current_minutes_watched=0,
                        current_subs=0,
                        drop_instance_id="1234",
                        is_claimed=True,
                    )
                ],
            ),
            # Valid
            "4567": Campaign(
                _id="4567",
                name="campaign2",
                game=None,
                status="",
                end_at=datetime.datetime.now(datetime.timezone.utc),
                start_at=datetime.datetime.now(datetime.timezone.utc),
                is_account_connected=True,
                account_link_url="https://example.com/",
                drops=[
                    Drop(
                        _id="1234",
                        name="test drop name",
                        end_at=MagicMock(),
                        start_at=MagicMock(),
                        benefits=[],
                        minutes_required=0,
                        subs_required=0,
                        current_minutes_watched=0,
                        current_subs=0,
                        drop_instance_id="1234",
                        is_claimed=False,
                    )
                ],
            ),
        },
        1,
    ),
]


@pytest.mark.parametrize("campaigns,expected_calls", test_claim_all_drops_data)
def test_claim_all_drops(campaigns: dict[str, Campaign], expected_calls: int):
    streamers = []
    campaign_store = dict()
    twitch = MagicMock()
    event_manager = MagicMock()
    system = DropsSystem(
        streamers=streamers,
        campaigns=campaign_store,
        twitch=twitch,
        event_manager=event_manager,
    )
    system.campaigns = campaigns
    system.claim_drop = MagicMock()
    # Set the threshold to max to avoid refreshing
    system.inventory_update_threshold = datetime.timedelta.max
    system.inventory_updated = datetime.datetime.now()

    system.claim_all_drops()

    assert system.claim_drop.call_count == expected_calls


test_drop_progress_data = [
    (
        Campaign(
            _id="01a169e3-6780-7212-83f7-878d9f619d27",
            game=None,
            name="campaign1",
            status="",
            end_at=datetime.datetime.fromisoformat("2026-10-23T18:50:00Z"),
            start_at=datetime.datetime.fromisoformat("2026-10-16T18:50:00Z"),
            is_account_connected=False,
            account_link_url=None,
            drops=[
                Drop(
                    _id="01a169e5-0140-7011-a211-e41ca803eef4",
                    name="drop1",
                    benefits=["1", "2"],
                    minutes_required=30,
                    subs_required=0,
                    end_at=datetime.datetime.fromisoformat("2026-10-23T18:50:00Z"),
                    start_at=datetime.datetime.fromisoformat("2026-10-16T18:50:00Z"),
                    drop_instance_id=None,
                    current_minutes_watched=0,
                    current_subs=0,
                    is_claimed=False,
                )
            ],
        ),
        DropProgress(
            drop_id="01a169e5-0140-7011-a211-e41ca803eef4",
            channel_id="1234",
            current_progress_min=15,
            required_progress_min=30,
            required_progress=30,
            current_progress=15,
            progress_type="minutes_watched",
            is_sitewide=False,
        ),
        Drop(
            _id="01a169e5-0140-7011-a211-e41ca803eef4",
            name="drop1",
            benefits=["1", "2"],
            minutes_required=30,
            subs_required=0,
            end_at=datetime.datetime.fromisoformat("2026-10-23T18:50:00Z"),
            start_at=datetime.datetime.fromisoformat("2026-10-16T18:50:00Z"),
            drop_instance_id=None,
            current_minutes_watched=15,
            current_subs=0,
            is_claimed=False,
        ),
    )
]


@pytest.mark.parametrize("campaign,progress,expected", test_drop_progress_data)
def test_drop_progress(campaign: Campaign, progress: DropProgress, expected: Drop):
    streamers = [Streamer(username="test", channel_id="1234")]
    campaigns = dict() if campaign is None else {campaign.id: campaign}
    twitch = MagicMock()
    event_manager = MagicMock()
    system = DropsSystem(
        streamers=streamers,
        campaigns=campaigns,
        twitch=twitch,
        event_manager=event_manager,
    )
    system._refresh_inventory = MagicMock()

    system.drop_progress(progress)

    drop = campaign.drops[expected.id]
    assert drop.id == expected.id
    assert drop.name == expected.name
    assert drop.benefit == expected.benefit
    assert drop.minutes_required == expected.minutes_required
    assert drop.subs_required == expected.subs_required
    assert drop.has_preconditions_met == expected.has_preconditions_met
    assert drop.current_minutes_watched == expected.current_minutes_watched
    assert drop.current_subs == expected.current_subs
    assert drop.drop_instance_id == expected.drop_instance_id
    assert drop.is_claimed == expected.is_claimed
    assert drop.is_claimable == expected.is_claimable
    assert drop.percentage_progress == expected.percentage_progress
    assert drop.end_at == expected.end_at
    assert drop.start_at == expected.start_at
