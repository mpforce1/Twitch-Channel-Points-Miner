import datetime
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.Drop import Drop


def drop(
    _id,
    name=None,
    benefits=None,
    minutes_required=None,
    subs_required=None,
    end_at=None,
    start_at=None,
    drop_instance_id=None,
    current_minutes_watched=None,
    current_subs=None,
    is_claimed=None,
):
    return Drop(
        _id=_id,
        name="drop name" if name is None else name,
        benefits=["a", "b"] if benefits is None else benefits,
        minutes_required=30 if minutes_required is None else minutes_required,
        subs_required=0 if subs_required is None else subs_required,
        end_at=(
            datetime.datetime.fromisoformat("2026-10-23T19:10:00Z")
            if end_at is None
            else end_at
        ),
        start_at=(
            datetime.datetime.fromisoformat("2026-10-16T19:10:00Z")
            if start_at is None
            else start_at
        ),
        drop_instance_id=None if drop_instance_id is None else drop_instance_id,
        current_minutes_watched=(
            0 if current_minutes_watched is None else current_minutes_watched
        ),
        current_subs=0 if current_subs is None else current_subs,
        is_claimed=False if is_claimed is None else is_claimed,
    )


def campaign(
    _id=None,
    game=None,
    name=None,
    status=None,
    end_at=None,
    start_at=None,
    is_account_connected=None,
    account_link_url=None,
    drops=None,
):
    return Campaign(
        _id="01a169f5-3338-7172-ad0b-5f96344e6297" if _id is None else _id,
        game=None if game is None else game,
        name="campaign name" if name is None else name,
        status="" if status is None else status,
        end_at=(
            datetime.datetime.fromisoformat("2026-10-23T19:10:00Z")
            if end_at is None
            else end_at
        ),
        start_at=(
            datetime.datetime.fromisoformat("2026-10-16T19:10:00Z")
            if start_at is None
            else start_at
        ),
        is_account_connected=(
            False if is_account_connected is None else is_account_connected
        ),
        account_link_url=None if account_link_url is None else account_link_url,
        drops=(
            [
                drop(_id="01a169fa-5fe8-776b-95fd-306cb0b7542d"),
                drop(_id="01a169fa-8f51-730c-b537-bc8cade4086e"),
            ]
            if drops is None
            else drops
        ),
    )


test_any_drop_claimable_data = [
    # No drops
    (
        campaign(
            drops=[],
        ),
        False,
    ),
    # Unclaimable drops
    (
        campaign(
            drops=[
                drop(_id="01a16d1b-aa2c-72b0-b445-eb27216128c1", is_claimed=True),
                drop(
                    _id="01a16d1b-e734-7774-b86c-26e0885ca5f1",
                    is_claimed=False,
                    drop_instance_id=None,
                ),
                drop(
                    _id="01a16d1c-0154-7142-9834-9d74c5262018",
                    is_claimed=False,
                    drop_instance_id="01a16d11-f876-7013-9957-c40bbb23fcd1",
                    subs_required=1,
                ),
            ]
        ),
        False,
    ),
    # Claimable drops
    (
        campaign(
            drops=[
                drop(
                    _id="01a16d1c-24e4-7042-a710-d1750a965212",
                    is_claimed=False,
                    drop_instance_id="01a16d12-aa0c-72f5-9c32-7bf70834bc1b",
                    subs_required=0,
                )
            ]
        ),
        True,
    ),
    # A mix
    (
        campaign(
            drops=[
                drop(
                    _id="01a16d1c-408d-7162-aabc-0e81cda76670",
                    is_claimed=False,
                    drop_instance_id="01a16d13-3214-7063-8259-fd2a6b5750c5",
                    subs_required=0,
                ),
                drop(
                    _id="01a16d1c-5764-76c5-85d2-b70c4bec4bd0",
                    is_claimed=False,
                    drop_instance_id="01a16d12-aa0c-72f5-9c32-7bf70834bc1b",
                    subs_required=1,
                ),
                drop(
                    _id="01a16d1c-6cd4-76b4-8891-6fd7003fb1df",
                    is_claimed=False,
                    drop_instance_id=None,
                ),
                drop(_id="01a16d1c-85a4-7048-ac64-1b6799b7273a", is_claimed=True),
            ]
        ),
        True,
    ),
]


@pytest.mark.parametrize("campaign,expected", test_any_drop_claimable_data)
def test_any_drop_claimable(campaign: Campaign, expected: bool):
    assert campaign.any_drop_claimable() == expected


test_ended_data = [
    (
        campaign(end_at=datetime.datetime.fromisoformat("2026-10-24T09:56:00Z")),
        datetime.datetime.fromisoformat("2026-10-24T10:00:00Z"),
        True,
    ),
    (
        campaign(end_at=datetime.datetime.fromisoformat("2026-10-24T09:56:00Z")),
        datetime.datetime.fromisoformat("2026-10-24T09:00:00Z"),
        False,
    ),
]


@pytest.mark.parametrize("campaign,now,expected", test_ended_data)
def test_ended(campaign: Campaign, now: datetime.datetime, expected: bool):
    with pytest.MonkeyPatch.context() as patcher:
        # Setup datetime.now patch
        mock_datetime = MagicMock()
        mock_datetime.now = MagicMock()
        mock_datetime.now.return_value = now
        patcher.setattr(datetime, "datetime", mock_datetime)

        assert campaign.ended() == expected


def test_progressable_drops():
    # Trivial
    pass


def test_any_drop_progressable():
    # Trivial
    pass


test_requires_account_link_data = [
    # Account connected
    (campaign(is_account_connected=True), False),
    # URL is None
    (campaign(is_account_connected=False, account_link_url=None), False),
    # URL is empty
    (campaign(is_account_connected=False, account_link_url=" "), False),
    # URL isn't a valid URL
    (
        campaign(is_account_connected=False, account_link_url="an invalid url string"),
        True,
    ),
    (campaign(is_account_connected=False, account_link_url="twitch.tv"), True),
    # URL doesn't contain twitch.tv
    (
        campaign(is_account_connected=False, account_link_url="https://example.com/"),
        True,
    ),
    # URL does contain twitch.tv
    (
        campaign(
            is_account_connected=False, account_link_url="https://twitch.tv/some-path/"
        ),
        False,
    ),
    (
        campaign(is_account_connected=False, account_link_url="https://twitch.tv/"),
        False,
    ),
    (campaign(is_account_connected=False, account_link_url="https://twitch.tv"), False),
    (
        campaign(
            is_account_connected=False, account_link_url="https://help.twitch.tv/"
        ),
        False,
    ),
]


@pytest.mark.parametrize("campaign,expected", test_requires_account_link_data)
def test_requires_account_link(campaign: Campaign, expected: bool):
    assert campaign.requires_account_link() == expected


test_progressable_data = [
    # Ended
    (
        campaign(end_at=datetime.datetime.fromisoformat("2026-10-24T09:00:00Z")),
        False,
        datetime.datetime.fromisoformat("2026-10-24T10:00:00Z"),
        False,
    ),
    # Not connected
    (
        campaign(
            end_at=datetime.datetime.fromisoformat("2026-10-24T11:00:00Z"),
            is_account_connected=False,
        ),
        False,
        datetime.datetime.fromisoformat("2026-10-24T10:00:00Z"),
        False,
    ),
    # No progressable drops
    (
        campaign(
            end_at=datetime.datetime.fromisoformat("2026-10-24T11:00:00Z"),
            is_account_connected=False,
            drops=[
                drop(
                    _id="01a16d3f-4d94-7691-86e2-0c40199bd916",
                    minutes_required=30,
                    current_minutes_watched=30,
                )
            ],
        ),
        True,
        datetime.datetime.fromisoformat("2026-10-24T10:00:00Z"),
        False,
    ),
    (
        campaign(
            end_at=datetime.datetime.fromisoformat("2026-10-24T11:00:00Z"),
            is_account_connected=True,
            drops=[
                drop(
                    _id="01a16d3f-4d94-7691-86e2-0c40199bd916",
                    minutes_required=30,
                    current_minutes_watched=30,
                )
            ],
        ),
        False,
        datetime.datetime.fromisoformat("2026-10-24T10:00:00Z"),
        False,
    ),
    # Progressable drops
    (
        campaign(
            end_at=datetime.datetime.fromisoformat("2026-10-24T11:00:00Z"),
            is_account_connected=False,
            drops=[
                drop(
                    _id="01a16d3f-4d94-7691-86e2-0c40199bd916",
                    minutes_required=30,
                    current_minutes_watched=0,
                )
            ],
        ),
        True,
        datetime.datetime.fromisoformat("2026-10-24T10:00:00Z"),
        True,
    ),
]


@pytest.mark.parametrize("campaign,allow_unlinked,now,expected", test_progressable_data)
def test_progressable(
    campaign: Campaign, allow_unlinked: bool, now: datetime.datetime, expected: bool
):
    with pytest.MonkeyPatch.context() as patcher:
        # Setup datetime.now patch
        mock_datetime = MagicMock()
        mock_datetime.now = MagicMock()
        mock_datetime.now.return_value = now
        patcher.setattr(datetime, "datetime", mock_datetime)

        assert campaign.progressable(allow_unlinked) == expected


test_drop_0 = drop(
    _id="01a16d44-a0bc-75f0-ab66-a24b8ce9ca91",
    minutes_required=15,
    current_minutes_watched=0,
)
test_drop_1 = drop(
    _id="01a16d51-140c-71d4-b169-9d21ced63189",
    minutes_required=30,
    current_minutes_watched=0,
)
test_drop_2 = drop(
    _id="01a16d53-5c44-770b-ba53-854cfb38f44f",
    minutes_required=5,
    current_minutes_watched=5,
)
test_current_drop_data = [
    # No drops
    (
        campaign(drops=[]),
        False,
        None,
    ),
    (
        campaign(
            drops=[],
        ),
        True,
        None,
    ),
    # All drops completed
    (
        campaign(
            drops=[
                drop(
                    _id="01a16d4e-b64c-7332-acb8-d44aa5013124",
                    minutes_required=15,
                    current_minutes_watched=15,
                ),
                drop(
                    _id="01a16d50-2f34-7243-bd8b-680df0dd695e",
                    minutes_required=30,
                    current_minutes_watched=30,
                ),
            ]
        ),
        True,
        None,
    ),
    # No drops completed
    (
        campaign(
            is_account_connected=False,
            drops=[
                test_drop_0,
                test_drop_1,
            ],
        ),
        False,
        None,
    ),
    (
        campaign(
            is_account_connected=True,
            drops=[
                test_drop_0,
                test_drop_1,
            ],
        ),
        True,
        test_drop_0,
    ),
    # Some drops completed
    (
        campaign(
            is_account_connected=False,
            drops=[
                test_drop_2,
                test_drop_0,
                test_drop_1,
            ],
        ),
        False,
        None,
    ),
    (
        campaign(
            is_account_connected=True,
            drops=[
                test_drop_2,
                test_drop_0,
                test_drop_1,
            ],
        ),
        True,
        test_drop_0,
    ),
]


@pytest.mark.parametrize("campaign,allow_unlinked,expected", test_current_drop_data)
def test_current_drop(campaign: Campaign, allow_unlinked: bool, expected: Drop | None):
    assert campaign.current_drop(allow_unlinked) == expected
