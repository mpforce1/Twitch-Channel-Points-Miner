import datetime
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropCampaignInProgress,
    DropsError,
    DropsPageClaimDropsResponse,
    InventoryResponse,
    TimeBasedDropInProgress,
)
from TwitchChannelPointsMiner.classes.systems.Drops import DropsSystem

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
    twitch = MagicMock()
    event_manager = MagicMock()
    system = DropsSystem(
        streamers=streamers,
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
        inventory = system._refresh_inventory()

        # Check result
        if expected:
            twitch.gql.get_inventory.assert_called_once()
            assert inventory == new_inventory
            assert system.inventory == new_inventory
            assert system.inventory_updated == now
        else:
            twitch.gql.get_inventory.assert_not_called()
            assert inventory != new_inventory
            assert system.inventory != new_inventory
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
    twitch = MagicMock()
    event_manager = MagicMock()
    system = DropsSystem(
        streamers=streamers,
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
    (None, 0),
    (InventoryResponse(None), 0),
    (InventoryResponse([]), 0),
    # No valid campaigns
    (
        InventoryResponse(
            [
                # Not connected
                DropCampaignInProgress(
                    _id="1234",
                    is_account_connected=False,
                    time_based_drops=[],
                ),
                # No drops
                DropCampaignInProgress(
                    _id="2345",
                    is_account_connected=True,
                    time_based_drops=[],
                ),
                # Already claimed
                DropCampaignInProgress(
                    _id="3456",
                    is_account_connected=True,
                    time_based_drops=[
                        TimeBasedDropInProgress(
                            _id="1234",
                            name="test drop name",
                            end_at=MagicMock(),
                            start_at=MagicMock(),
                            benefits=[],
                            required_minutes_watched=0,
                            required_subs=0,
                            self_edge=TimeBasedDropInProgress.SelfEdge(
                                has_preconditions_met=True,
                                current_minutes_watched=0,
                                current_subs=0,
                                drop_instance_id="1234",
                                is_claimed=True,
                            ),
                        )
                    ],
                ),
                # No drop instance id
                DropCampaignInProgress(
                    _id="3456",
                    is_account_connected=True,
                    time_based_drops=[
                        TimeBasedDropInProgress(
                            _id="1234",
                            name="test drop name",
                            end_at=MagicMock(),
                            start_at=MagicMock(),
                            benefits=[],
                            required_minutes_watched=0,
                            required_subs=0,
                            self_edge=TimeBasedDropInProgress.SelfEdge(
                                has_preconditions_met=True,
                                current_minutes_watched=0,
                                current_subs=0,
                                drop_instance_id=None,
                                is_claimed=False,
                            ),
                        )
                    ],
                ),
            ]
        ),
        0,
    ),
    # Some valid
    (
        InventoryResponse(
            [
                # Already claimed
                DropCampaignInProgress(
                    _id="3456",
                    is_account_connected=True,
                    time_based_drops=[
                        TimeBasedDropInProgress(
                            _id="1234",
                            name="test drop name",
                            end_at=MagicMock(),
                            start_at=MagicMock(),
                            benefits=[],
                            required_minutes_watched=0,
                            required_subs=0,
                            self_edge=TimeBasedDropInProgress.SelfEdge(
                                has_preconditions_met=True,
                                current_minutes_watched=0,
                                current_subs=0,
                                drop_instance_id="1234",
                                is_claimed=True,
                            ),
                        )
                    ],
                ),
                # Valid
                DropCampaignInProgress(
                    _id="3456",
                    is_account_connected=True,
                    time_based_drops=[
                        TimeBasedDropInProgress(
                            _id="1234",
                            name="test drop name",
                            end_at=MagicMock(),
                            start_at=MagicMock(),
                            benefits=[],
                            required_minutes_watched=0,
                            required_subs=0,
                            self_edge=TimeBasedDropInProgress.SelfEdge(
                                has_preconditions_met=True,
                                current_minutes_watched=0,
                                current_subs=0,
                                drop_instance_id="1234",
                                is_claimed=False,
                            ),
                        )
                    ],
                ),
            ]
        ),
        1,
    ),
]


@pytest.mark.parametrize("inventory,expected_calls", test_claim_all_drops_data)
def test_claim_all_drops(inventory: InventoryResponse | None, expected_calls: int):
    streamers = []
    twitch = MagicMock()
    event_manager = MagicMock()
    system = DropsSystem(
        streamers=streamers,
        twitch=twitch,
        event_manager=event_manager,
    )
    system.inventory = inventory
    system.claim_drop = MagicMock()
    # Set the threshold to max to avoid refreshing
    system.inventory_update_threshold = datetime.timedelta.max

    system.claim_all_drops()

    assert system.claim_drop.call_count == expected_calls


test_progress_bar_data = [
    (0, 0, 10, "|          |\t0.00% [0/0]"),
    (0, 15, 10, "|          |\t0.00% [0/15]"),
    (1, 15, 10, "|          |\t6.67% [1/15]"),
    (2, 15, 10, "|█         |\t13.33% [2/15]"),
    (5, 15, 10, "|███       |\t33.33% [5/15]"),
    (7, 15, 10, "|████      |\t46.67% [7/15]"),
    (10, 15, 10, "|██████    |\t66.67% [10/15]"),
    (14, 15, 10, "|█████████ |\t93.33% [14/15]"),
    (15, 15, 10, "|██████████|\t100.00% [15/15]"),
]


@pytest.mark.parametrize("current,required,segments,expected", test_progress_bar_data)
def test_progress_bar(current: int, required: int, segments: int, expected: str):
    streamers = []
    twitch = MagicMock()
    event_manager = MagicMock()
    system = DropsSystem(
        streamers=streamers,
        twitch=twitch,
        event_manager=event_manager,
    )

    assert system._progress_bar(current, required, segments) == expected


def test_drop_progress():
    # Doesn't do enough to test
    pass
