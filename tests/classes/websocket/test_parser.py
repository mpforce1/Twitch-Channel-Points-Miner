import json
import os
import pathlib

import pytest

from TwitchChannelPointsMiner.classes.websocket.data import WeeklyRewards
from TwitchChannelPointsMiner.classes.websocket.data.OnsiteNotification import (
    UserDropRewardReminderNotification,
    UserEarnedQuestsRewardBadgeNotification,
)
from TwitchChannelPointsMiner.classes.websocket.data.Parser import (
    parse_wrapped_markdown_segment,
    Parser,
)

test_parse_wrapped_markdown_segment_data = [
    ('"some text"', '"', 0, "some text"),
    ('Text at the start "quoted text" text at the end', '"', 0, "quoted text"),
    ("**bold text**", "**", 0, "bold text"),
    ("Text at the start **bold text** text at the end", "**", 0, "bold text"),
    (
        'Text at the start "first quoted segment" text in the middle "second quoted segment" text at the end',
        '"',
        1,
        "second quoted segment",
    ),
    ('\\"some text\\"', '\\"', 0, "some text"),
    ('Text at the start \\"quoted text\\" text at the end', '\\"', 0, "quoted text"),
]


@pytest.mark.parametrize(
    "source,wrapper,index,expected", test_parse_wrapped_markdown_segment_data
)
def test_parse_wrapped_markdown_segment(
    source: str, wrapper: str, index: int, expected: str
):
    assert parse_wrapped_markdown_segment(source, wrapper, index) == expected


@pytest.fixture
def parser():
    return Parser()


def read_data(filename: str):
    file = pathlib.Path(filename)
    with file.open("r"):
        return json.loads(file.read_text())


test_parse_onsite_notification_data = [
    (
        "tests/classes/websocket/test_data/onsite-notification-01.json",
        UserDropRewardReminderNotification(
            "Example Drop Reward",
            "https://example.com/path1/path2/019ec67b-10fa-723a-a4a6-832caa7e6e39.png",
        ),
    ),
    (
        "tests/classes/websocket/test_data/onsite-notification-01.json",
        UserDropRewardReminderNotification(
            "Example Drop Reward",
            "https://example.com/path1/path2/019ec67b-10fa-723a-a4a6-832caa7e6e39.png",
        ),
    ),
    ("tests/classes/websocket/test_data/onsite-notification-03.json", None),
]


@pytest.mark.parametrize("file,expected", test_parse_onsite_notification_data)
def test_parse_onsite_notification(parser: Parser, file: str, expected):
    data = read_data(file)
    assert parser.parse_onsite_notification(data) == expected

test_parse_weekly_rewards_data = [
    (
        "tests/classes/websocket/test_data/weekly-rewards-01.json",
        WeeklyRewards.Notification(
            viewer_id="123456789",
            channel_id="987654321",
            event_id="weekly-rewards-event-id",
            days_visited_this_week=2,
            accumulated_weeks=1,
            notification_type="PARTIAL_PROGRESS",
            current_reward=WeeklyRewards.Reward(
                tier=2,
                channel_points=250,
                badge_set_id="event-badge",
                badge_version="2",
            ),
            event_config=WeeklyRewards.Config(
                days_required_per_week=3
            )
        ),
    )
]


@pytest.mark.parametrize("file,expected", test_parse_weekly_rewards_data)
def test_parse_weekly_rewards(parser: Parser, file: str, expected):
    data = read_data(file)
    assert parser.parse_weekly_rewards(data) == expected
