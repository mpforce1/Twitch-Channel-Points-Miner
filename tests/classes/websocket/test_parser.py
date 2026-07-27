import datetime
import json
import pathlib

import pytest

from TwitchChannelPointsMiner.classes.entities.GiftSub import GiftSub, Gifter, Target
from TwitchChannelPointsMiner.classes.gql.data.Parser import subscription_benefit_parser
from TwitchChannelPointsMiner.classes.websocket.data import WeeklyRewards
from TwitchChannelPointsMiner.classes.websocket.data import (
    CommunityPointsUser,
    Predictions,
    PredictionsChannel,
    PredictionsUser,
    Raid,
    VideoPlaybackById,
    WeeklyRewards,
)
from TwitchChannelPointsMiner.classes.websocket.data.OnsiteNotification import (
    UserDropRewardReminderNotification,
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
            event_config=WeeklyRewards.Config(days_required_per_week=3),
        ),
    )
]


@pytest.mark.parametrize("file,expected", test_parse_weekly_rewards_data)
def test_parse_weekly_rewards(parser: Parser, file: str, expected):
    data = read_data(file)
    assert parser.parse_weekly_rewards(data) == expected


test_parse_subscription_benefit_data = [
    (
        "tests/classes/websocket/test_data/subscription-benefit-01.json",
        GiftSub(
            _id="UEJOJOayCKcWGCBXdzmP0",
            target=None,
            gifter=Gifter(
                _id="123456789",
                username="testuser",
                display_name="TestUser",
            ),
            tier="Custom",
            display_name="Twitch Turbo",
            ends_at=datetime.datetime.fromisoformat("2026-07-15T14:13:12Z"),
        ),
    ),
    (
        "tests/classes/websocket/test_data/subscription-benefit-02.json",
        GiftSub(
            _id="01KYPKHE3WX1R2M9E15F8P5CZQ",
            target=Target(
                _id="123456789",
                username="testchanneluser",
                display_name="TestChannelUser",
            ),
            gifter=Gifter(
                _id="654321987",
                username="testgifteruser",
                display_name="TestGifterUser",
            ),
            tier=1,
            display_name="Subscription (testchanneluser)",
            ends_at=datetime.datetime.fromisoformat("2026-08-15T10:11:12Z"),
        ),
    ),
]


@pytest.mark.parametrize("file,expected", test_parse_subscription_benefit_data)
def test_parse_subscription_benefit(file: str, expected):
    data = read_data(file)
    assert subscription_benefit_parser(data) == expected


def file_json_test(filename, parser_function, expected):
    data = read_data(f"tests/classes/websocket/test_data/{filename}")
    assert parser_function(data) == expected


def test_parse_claim_available(parser: Parser):
    expected = CommunityPointsUser.ClaimAvailable(
        timestamp=datetime.datetime.fromisoformat("2026-07-14T05:42:18.541236Z"),
        channel_id="51564153",
        claim_id="019f99ee-4709-7193-8956-ead4a2efcb9f",
        amount=50,
    )
    file_json_test(
        "claim-available-01.json", parser.community_points_user_parser, expected
    )


def test_parse_event_created(parser: Parser):
    expected = PredictionsChannel.EventCreated(
        timestamp=datetime.datetime.fromisoformat("2026-07-24T01:04:12.135421874Z"),
        event=Predictions.PredictionEvent(
            id="019f99e5-2d1e-727b-8278-b6ff40c648bd",
            channel_id="789465324",
            created_at=datetime.datetime.fromisoformat(
                "2026-07-24T01:04:12.465321975Z"
            ),
            created_by=Predictions.User(
                id="4687218616",
                display_name="testuser",
            ),
            ended_at=None,
            ended_by=None,
            locked_at=None,
            locked_by=None,
            outcomes=[
                Predictions.Outcome(
                    id="019f99e6-2c65-7708-8d89-0dfd86fa482d",
                    color="BLUE",
                    title="outcome 1 title",
                    total_points=0,
                    total_users=0,
                    top_predictors=[],
                ),
                Predictions.Outcome(
                    id="019f99e7-81ad-7556-aea6-9b3a10ef04e5",
                    color="BLUE",
                    title="outcome 2 title",
                    total_points=0,
                    total_users=0,
                    top_predictors=[],
                ),
            ],
            prediction_window_seconds=60,
            status="ACTIVE",
            title="test event title",
            winning_outcome_id=None,
        ),
    )
    file_json_test("event-created-01.json", parser.predictions_channel_parser, expected)


def test_parse_event_updated(parser: Parser):
    expected = PredictionsChannel.EventUpdated(
        timestamp=datetime.datetime.fromisoformat("2026-07-24T01:36:58.463527948Z"),
        event=Predictions.PredictionEvent(
            id="019f99e5-2d1e-727b-8278-b6ff40c648bd",
            channel_id="789465324",
            created_at=datetime.datetime.fromisoformat(
                "2026-07-24T01:04:12.465321975Z"
            ),
            created_by=Predictions.User(
                id="4687218616",
                display_name="testuser",
            ),
            ended_at=None,
            ended_by=None,
            locked_at=None,
            locked_by=None,
            outcomes=[
                Predictions.Outcome(
                    id="019f99e6-2c65-7708-8d89-0dfd86fa482d",
                    color="BLUE",
                    title="outcome 1 title",
                    total_points=1000,
                    total_users=1,
                    top_predictors=[
                        Predictions.Prediction(
                            id="8b3d78aa0ea3d87ddf63373290c0fef211bbaac09cdf26af2e37203a35eb30b9",
                            event_id="019f99e5-2d1e-727b-8278-b6ff40c648bd",
                            outcome_id="019f99e6-2c65-7708-8d89-0dfd86fa482d",
                            channel_id="789465324",
                            points=1000,
                            predicted_at=datetime.datetime.fromisoformat(
                                "2026-07-24T01:36:58.463527948Z"
                            ),
                            updated_at=datetime.datetime.fromisoformat(
                                "2026-07-24T01:36:58.463527948Z"
                            ),
                            user_id="32658741",
                            result=None,
                            user_display_name="testuser2",
                        )
                    ],
                ),
                Predictions.Outcome(
                    id="019f99e7-81ad-7556-aea6-9b3a10ef04e5",
                    color="BLUE",
                    title="outcome 2 title",
                    total_points=4000,
                    total_users=1,
                    top_predictors=[
                        Predictions.Prediction(
                            id="ee416fe1c7d07ac9393e0582d3a4b508ec627f048d733806cbab366f367d6f49",
                            event_id="019f99e5-2d1e-727b-8278-b6ff40c648bd",
                            outcome_id="019f99e7-81ad-7556-aea6-9b3a10ef04e5",
                            channel_id="789465324",
                            points=4000,
                            predicted_at=datetime.datetime.fromisoformat(
                                "2026-07-24T01:35:10.574236512Z"
                            ),
                            updated_at=datetime.datetime.fromisoformat(
                                "2026-07-24T01:35:10.574236512Z"
                            ),
                            user_id="321568971",
                            result=None,
                            user_display_name="testuser3",
                        )
                    ],
                ),
            ],
            prediction_window_seconds=60,
            status="ACTIVE",
            title="test event title",
            winning_outcome_id=None,
        ),
    )
    file_json_test("event-updated-01.json", parser.predictions_channel_parser, expected)


def test_points_earned(parser: Parser):
    expected = CommunityPointsUser.PointsEarned(
        timestamp=datetime.datetime.fromisoformat("2026-07-14T01:10:50.457165464Z"),
        channel_id="456789415",
        amount=10,
        reason="WATCH",
        balance=646145,
    )
    file_json_test(
        "points-earned-01.json", parser.community_points_user_parser, expected
    )


def test_points_spent(parser: Parser):
    expected = CommunityPointsUser.PointsSpent(
        timestamp=datetime.datetime.fromisoformat("2026-07-24T14:35:10.456461684Z"),
        channel_id="48564615",
        balance=651614,
    )
    file_json_test(
        "points-spent-01.json", parser.community_points_user_parser, expected
    )


def test_prediction_made(parser: Parser):
    expected = PredictionsUser.PredictionMade(
        timestamp=datetime.datetime.fromisoformat("2026-07-24T18:36:21.746521389Z"),
        prediction=Predictions.Prediction(
            id="fe7bb40ca32435e021cbacc9682c7f8a809c77c28eaccadc6637c7fdcba75b8b",
            event_id="019f99df-c065-75f4-ae26-78a508ee47e0",
            outcome_id="019f99df-f9a5-71bf-bc4d-54180ec16772",
            channel_id="3461572836",
            points=100,
            predicted_at=datetime.datetime.fromisoformat(
                "2026-07-24T18:36:18.475125874Z"
            ),
            updated_at=datetime.datetime.fromisoformat(
                "2026-07-24T18:36:21.124537412Z"
            ),
            user_id="978645136",
            result=None,
            user_display_name=None,
        ),
    )
    file_json_test("prediction-made-01.json", parser.predictions_user_parser, expected)


def test_prediction_result(parser: Parser):
    expected = PredictionsUser.PredictionResult(
        timestamp=datetime.datetime.fromisoformat("2026-07-24T15:25:00.845731694Z"),
        prediction=Predictions.Prediction(
            id="210d75a0a9bce2e5f1ea792f9e4822b4d80c1709749c5aaf15fc9c751c03bbbe",
            event_id="019f99e2-36bd-76bc-9bd4-25f8e1e9fe4b",
            outcome_id="019f99e2-4d3d-75ca-a331-82e3ee7df213",
            channel_id="74513684",
            points=200,
            predicted_at=datetime.datetime.fromisoformat(
                "2026-07-24T14:34:00.145712546Z"
            ),
            updated_at=datetime.datetime.fromisoformat(
                "2026-07-24T14:34:00.145712546Z"
            ),
            user_id="584645315",
            result=Predictions.Result(
                type="LOSE",
                points_won=None,
            ),
            user_display_name=None,
        ),
    )
    file_json_test("prediction-result-01.json", parser.predictions_user_parser, expected)


def test_raid_update(parser: Parser):
    expected = Raid.RaidUpdate(
        id="019f99eb-20cd-72e0-b7b1-52b781e6c0d0",
        target_id="541678464",
        target_username="targetusername",
        target_display_name="TargetDisplayName",
    )
    file_json_test("raid-update-01.json", parser.raid_parser, expected)


def test_stream_down(parser: Parser):
    expected = VideoPlaybackById.StreamDown(
        timestamp=datetime.datetime.fromisoformat("2026-07-14T21:51:14Z")
    )
    file_json_test("stream-down-01.json", parser.video_playback_by_id_parser, expected)


def test_stream_up(parser: Parser):
    expected = VideoPlaybackById.StreamUp(
        timestamp=datetime.datetime.fromisoformat("2026-07-14T18:35:20Z")
    )
    file_json_test("stream-up-01.json", parser.video_playback_by_id_parser, expected)


def test_viewcount(parser: Parser):
    expected = VideoPlaybackById.ViewCount(
        timestamp=datetime.datetime.fromisoformat("2026-07-14T18:35:23.741259Z"),
        viewers=20,
    )
    file_json_test("viewcount-01.json", parser.video_playback_by_id_parser, expected)
