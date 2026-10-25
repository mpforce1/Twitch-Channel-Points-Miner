import datetime
import sys
from typing import Literal
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.Stream import Stream
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    DropsMode,
    HLSSettings,
    Streamer,
    StreamerSettings,
)
from tests.classes.entities.test_campaign import campaign, drop


class TestStreamer:
    update_history_data = [
        [[], {}, 0, True],
        [[["WATCH", 10, 1]], {"WATCH": {"amount": 10, "counter": 1}}, 1, True],
        [
            [["WATCH_STREAK", 300, 1]],
            {"WATCH_STREAK": {"amount": 300, "counter": 1}},
            0,
            False,
        ],
        [
            [["WATCH_STREAK", 300, 1], ["WATCH", 10, 1]],
            {
                "WATCH_STREAK": {"amount": 300, "counter": 1},
                "WATCH": {"amount": 10, "counter": 1},
            },
            1,
            False,
        ],
        [
            [["WATCH", 10, 1], ["WATCH", 10, 1]],
            {
                "WATCH": {"amount": 20, "counter": 2},
            },
            2,
            False,
        ],
        [
            [["WATCH", 10, 1], ["WATCH", 10, 1], ["WATCH_STREAK", 300, 1]],
            {
                "WATCH_STREAK": {"amount": 300, "counter": 1},
                "WATCH": {"amount": 20, "counter": 2},
            },
            2,
            False,
        ],
        [
            [
                ["WATCH", 10, 1],
                ["WATCH", 10, 1],
                ["WATCH_STREAK", 300, 1],
                ["WATCH", 10, 1],
                ["WATCH", 12, 1],
                ["WATCH", 12, 1],
            ],
            {
                "WATCH_STREAK": {"amount": 300, "counter": 1},
                "WATCH": {"amount": 54, "counter": 5},
            },
            5,
            False,
        ],
    ]

    @pytest.mark.parametrize(
        "updates,expected_counts,expected_stream_watch_count,expected_watch_streak_missing",
        update_history_data,
    )
    def test_update_history(
        self,
        updates: list,
        expected_counts: dict,
        expected_stream_watch_count: int,
        expected_watch_streak_missing: bool,
    ):
        streamer = Streamer("test_username")

        for update in updates:
            streamer.update_history(update[0], update[1], update[2])

        assert len(streamer.history) == len(expected_counts)
        for reason in expected_counts.keys():
            assert streamer.history[reason] == expected_counts[reason]

        assert streamer.stream.watch_count == expected_stream_watch_count
        assert streamer.stream.watch_streak_missing == expected_watch_streak_missing


test_watch_all_segments_data = [
    ("enable", False, True),
    ("enable", True, True),
    ("disable", False, False),
    ("disable", True, False),
    ("drops", False, False),
    ("drops", True, True),
]


@pytest.mark.parametrize("setting,has_drops,expected", test_watch_all_segments_data)
def test_watch_all_segments(
    setting: Literal["enable", "disable", "drops"], has_drops: bool, expected: bool
):
    with pytest.MonkeyPatch().context() as patcher:
        any_campaign_has_progressable_drop = MagicMock()
        any_campaign_has_progressable_drop.return_value = has_drops
        patcher.setattr(
            Streamer,
            "any_campaign_has_progressable_drop",
            any_campaign_has_progressable_drop,
        )
        streamer = Streamer(
            "",
            "",
            settings=StreamerSettings(
                simulate_hls_playback=HLSSettings(
                    refresh_before=0, watch_all_segments=setting
                )
            ),
        )

        assert streamer.watch_all_segments(dict()) == expected


def test_allows_unlinked_drops():
    # Trivial
    pass


campaign_a = campaign(_id="86bfd518-f874-4ade-bfd5-18f8744ade4a")
campaign_b = campaign(_id="e7e5a1bd-97b0-4710-a5a1-bd97b02710de")
campaign_c = campaign(_id="3bd7627b-b049-4b68-9762-7bb0491b68e0")
test_campaigns_data = [
    # No campaigns
    ([], [], []),
    # No streamer campaigns
    ([], [campaign_a, campaign_b, campaign_c], []),
    # All campaigns
    (
        [
            "86bfd518-f874-4ade-bfd5-18f8744ade4a",
            "e7e5a1bd-97b0-4710-a5a1-bd97b02710de",
            "3bd7627b-b049-4b68-9762-7bb0491b68e0",
        ],
        [campaign_a, campaign_b, campaign_c],
        [campaign_a, campaign_b, campaign_c],
    ),
    # Mixed
    (
        [
            "86bfd518-f874-4ade-bfd5-18f8744ade4a",
            "3bd7627b-b049-4b68-9762-7bb0491b68e0",
            "edd541c9-63f1-4069-9541-c963f1c06935",
        ],
        [campaign_a, campaign_b, campaign_c],
        [campaign_a, campaign_c],
    ),
]


@pytest.mark.parametrize("campaign_ids,campaigns,expected", test_campaigns_data)
def test_campaigns(
    campaign_ids: list[str], campaigns: list[Campaign], expected: list[Campaign]
):
    stream = Stream()
    stream.campaigns = campaign_ids
    streamer = Streamer("1234", stream=stream)

    streamer_campaigns = list(
        streamer.campaigns({campaign.id: campaign for campaign in campaigns})
    )

    # Check lists for equivalency
    for campaign in expected:
        assert campaign in streamer_campaigns
    for campaign in streamer_campaigns:
        assert campaign in expected


def test_progressable_campaigns():
    # Trivial
    pass


def test_current_drops():
    # Trivial
    pass


def test_any_campaign_has_progressable_drop():
    # Trivial
    pass


def test_remaining_drop_count():
    # Trivial
    pass


test_min_drop_end_date_data = [
    # No campaigns
    (
        [],
        None,
    ),
    # Some campaigns
    (
        [
            campaign(
                _id="01a16d5c-36e6-726f-a4ba-0cacfed3ba9d",
                end_at=datetime.datetime.fromisoformat("2026-10-24T11:00:00Z"),
            ),
            campaign(
                _id="01a16d5d-a17f-7333-9330-488bc93a3dd6",
                end_at=datetime.datetime.fromisoformat("2026-10-24T18:00:00Z"),
            ),
            campaign(
                _id="01a16d5e-0c9c-75a4-bf74-db15e56a3a9a",
                end_at=datetime.datetime.fromisoformat("2026-10-23T11:00:00Z"),
            ),
        ],
        datetime.datetime.fromisoformat("2026-10-23T11:00:00Z"),
    ),
    (
        [
            campaign(
                _id="f8dbecb3-a537-43d5-9bec-b3a53753d5d8",
                end_at=datetime.datetime.fromisoformat("2026-10-24T11:00:00Z"),
            ),
            campaign(
                _id="c4f77d2e-bbdc-4c16-b77d-2ebbdc8c16ac",
                end_at=datetime.datetime.fromisoformat("2026-10-24T09:00:00Z"),
            ),
            campaign(
                _id="5906b583-3af5-4abc-86b5-833af53abce6",
                end_at=datetime.datetime.fromisoformat("2026-10-23T05:00:00Z"),
            ),
        ],
        datetime.datetime.fromisoformat("2026-10-23T05:00:00Z"),
    ),
]


@pytest.mark.parametrize("campaigns,expected", test_min_drop_end_date_data)
def test_min_drop_end_date(
    campaigns: list[Campaign], expected: datetime.datetime | None
):
    streamer = Streamer("1234")
    with pytest.MonkeyPatch.context() as patcher:
        # Set up Streamer.progressable_campaigns
        patcher.setattr(Streamer, "progressable_campaigns", lambda a, b: campaigns)

        assert (
            streamer.min_drop_end_date(
                {campaign.id: campaign for campaign in campaigns}
            )
            == expected
        )


test_max_drop_end_date_data = [
    # No campaigns
    (
        [],
        None,
    ),
    # Some campaigns
    (
        [
            campaign(
                _id="01a16d5c-36e6-726f-a4ba-0cacfed3ba9d",
                end_at=datetime.datetime.fromisoformat("2026-10-24T18:00:00Z"),
            ),
            campaign(
                _id="01a16d5d-a17f-7333-9330-488bc93a3dd6",
                end_at=datetime.datetime.fromisoformat("2026-10-24T09:00:00Z"),
            ),
            campaign(
                _id="01a16d5e-0c9c-75a4-bf74-db15e56a3a9a",
                end_at=datetime.datetime.fromisoformat("2026-10-23T11:00:00Z"),
            ),
        ],
        datetime.datetime.fromisoformat("2026-10-24T18:00:00Z"),
    ),
    (
        [
            campaign(
                _id="f8dbecb3-a537-43d5-9bec-b3a53753d5d8",
                end_at=datetime.datetime.fromisoformat("2026-10-23T11:00:00Z"),
            ),
            campaign(
                _id="c4f77d2e-bbdc-4c16-b77d-2ebbdc8c16ac",
                end_at=datetime.datetime.fromisoformat("2026-10-24T09:00:00Z"),
            ),
            campaign(
                _id="5906b583-3af5-4abc-86b5-833af53abce6",
                end_at=datetime.datetime.fromisoformat("2026-10-23T11:00:00Z"),
            ),
        ],
        datetime.datetime.fromisoformat("2026-10-24T09:00:00Z"),
    ),
]


@pytest.mark.parametrize("campaigns,expected", test_max_drop_end_date_data)
def test_max_drop_end_date(
    campaigns: list[Campaign], expected: datetime.datetime | None
):
    streamer = Streamer("1234")
    with pytest.MonkeyPatch.context() as patcher:
        # Set up Streamer.progressable_campaigns
        patcher.setattr(Streamer, "progressable_campaigns", lambda a, b: campaigns)

        assert (
            streamer.max_drop_end_date(
                {campaign.id: campaign for campaign in campaigns}
            )
            == expected
        )


test_min_drop_progress_data = [
    # No drops
    (
        [],
        None,
    ),
    # Mixed drops
    (
        [
            # 0 mins
            drop(
                _id="273c3ca3-4ea9-47ba-bc3c-a34ea917bac9",
                current_minutes_watched=0,
            ),
            # 10 mins
            drop(
                _id="ffb63dab-2f85-4495-b63d-ab2f8544953e",
                current_minutes_watched=10,
            ),
            # 5 mins
            drop(
                _id="69746741-1871-4bf5-b467-411871cbf5ab",
                current_minutes_watched=5,
            ),
        ],
        0,
    ),
]


@pytest.mark.parametrize("drops,expected", test_min_drop_progress_data)
def test_min_drop_progress(drops: list[Drop], expected: int):
    streamer = Streamer("1234")
    with pytest.MonkeyPatch.context() as patcher:
        # Set up Streamer.current_drops
        patcher.setattr(Streamer, "current_drops", lambda a, b: drops)

        assert streamer.min_drop_progress(MagicMock()) == expected


test_max_drop_progress_data = [
    # No drops
    (
        [],
        None,
    ),
    # Mixed drops
    (
        [
            # 0 mins
            drop(
                _id="60eb8c0c-8aac-4625-ab8c-0c8aac462599",
                current_minutes_watched=0,
            ),
            # 10 mins
            drop(
                _id="9e4ae1e3-b46b-44a5-8ae1-e3b46b14a508",
                current_minutes_watched=10,
            ),
            # 5 mins
            drop(
                _id="065b33fe-54a7-4d73-9b33-fe54a7bd73cb",
                current_minutes_watched=5,
            ),
        ],
        10,
    ),
]


@pytest.mark.parametrize("drops,expected", test_max_drop_progress_data)
def test_max_drop_progress(drops: list[Drop], expected: int):
    streamer = Streamer("1234")
    with pytest.MonkeyPatch.context() as patcher:
        # Set up Streamer.current_drops
        patcher.setattr(Streamer, "current_drops", lambda a, b: drops)

        assert streamer.max_drop_progress(MagicMock()) == expected


test_min_drop_percentage_progress_data = [
    # No drops
    (
        [],
        None,
    ),
    # Mixed drops
    (
        [
            # 0%
            drop(
                _id="5fa3c65e-be06-4f3a-a3c6-5ebe06bf3ad2",
                current_minutes_watched=0,
                minutes_required=10,
            ),
            # 50%
            drop(
                _id="9fa1307e-6287-4be5-a130-7e62871be5ee",
                current_minutes_watched=10,
                minutes_required=20,
            ),
            # 8%
            drop(
                _id="f92e1b76-a15b-40e7-ae1b-76a15b40e7ef",
                current_minutes_watched=5,
                minutes_required=40,
            ),
        ],
        0,
    ),
]


@pytest.mark.parametrize("drops,expected", test_min_drop_percentage_progress_data)
def test_min_drop_percentage_progress(drops: list[Drop], expected: int):
    streamer = Streamer("1234")
    with pytest.MonkeyPatch.context() as patcher:
        # Set up Streamer.current_drops
        patcher.setattr(Streamer, "current_drops", lambda a, b: drops)

        assert streamer.min_drop_percentage_progress(MagicMock()) == expected


test_max_drop_percentage_progress_data = [
    # No drops
    (
        [],
        None,
    ),
    # Mixed drops
    (
        [
            # 0%
            drop(
                _id="8065f209-eec9-49e2-a5f2-09eec9b9e248",
                current_minutes_watched=0,
                minutes_required=100
            ),
            # 16.66%
            drop(
                _id="991da0db-7b7c-457f-9da0-db7b7cc57fb7",
                current_minutes_watched=10,
                minutes_required=60
            ),
            # 25%
            drop(
                _id="1638f567-75df-419d-b8f5-6775df519d7c",
                current_minutes_watched=5,
                minutes_required=20,
            ),
        ],
        0.25,
    ),
]


@pytest.mark.parametrize("drops,expected", test_max_drop_percentage_progress_data)
def test_max_drop_percentage_progress(drops: list[Drop], expected: int):
    streamer = Streamer("1234")
    with pytest.MonkeyPatch.context() as patcher:
        # Set up Streamer.current_drops
        patcher.setattr(Streamer, "current_drops", lambda a, b: drops)

        assert streamer.max_drop_percentage_progress(MagicMock()) == expected

