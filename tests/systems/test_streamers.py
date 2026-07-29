import datetime
from threading import stack_size
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.CommunityGoal import CommunityGoal
from TwitchChannelPointsMiner.classes.entities.Raid import Raid
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import (
    BonusPointsAvailable,
    JoinRaid,
    MomentClaim,
    WatchStreakRecovery,
)
from TwitchChannelPointsMiner.classes.websocket.data import (
    CommunityPointsChannel,
    CommunityPointsUser,
    ViewerMilestones,
    WeeklyRewards,
)
from TwitchChannelPointsMiner.classes.websocket.data.Raid import RaidUpdate
from TwitchChannelPointsMiner.classes.websocket.data.UserSubscribeEvents import (
    UserSubscribed,
)
from TwitchChannelPointsMiner.systems.Streamers import StreamerSystem

Settings.enable_analytics = False


@pytest.fixture
def system():
    return StreamerSystem(
        twitch=MagicMock(),
        streamers=[],
        event_manager=MagicMock(),
    )


@pytest.fixture
def streamer():
    streamer = MagicMock()
    streamer.channel_id = "123456"
    return streamer


@pytest.mark.parametrize("enable_analytics", [False, True])
def test__update_points_change(system, enable_analytics: bool):
    streamer = MagicMock()
    balance = 10001
    reason = "WATCH"

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(Settings, "enable_analytics", enable_analytics)
        system._update_points_change(streamer, balance, reason)

    assert streamer.channel_points == balance
    if enable_analytics:
        streamer.persistent_series.assert_called_once_with(event_type=reason)


def test_points_earned(system):
    channel_id = "12345"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]
    system._update_points_change = MagicMock()

    data = CommunityPointsUser.PointsEarned(
        timestamp=datetime.datetime.fromtimestamp(123456),
        channel_id=channel_id,
        amount=100,
        reason="WATCH_STREAK",
        balance=2000,
    )

    system.points_earned(data)

    system._update_points_change.assert_called_once()
    system.event_manager.manage.assert_called_once()


def test_points_spent(system):
    channel_id = "12345"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]
    system._update_points_change = MagicMock()

    data = CommunityPointsUser.PointsSpent(
        timestamp=datetime.datetime.fromtimestamp(123456),
        channel_id=channel_id,
        balance=1000,
    )

    system.points_spent(data)

    system._update_points_change.assert_called_once()
    system.event_manager.manage.assert_called_once()


def test_claim_available(system):
    data = CommunityPointsUser.ClaimAvailable(
        timestamp=datetime.datetime.fromtimestamp(1234567),
        channel_id="123456",
        claim_id="019fa90b-6d10-71af-a9e0-024c379fbc83",
        amount=100,
    )

    system.claim_available(data)

    system.event_manager.manage.assert_called_once_with(
        BonusPointsAvailable(
            timestamp=datetime.datetime.fromtimestamp(1234567),
            channel_id="123456",
            claim_id="019fa90b-6d10-71af-a9e0-024c379fbc83",
            amount=100,
        )
    )


def test_raid_update(system):
    streamer = MagicMock()
    streamer.channel_id = "12345"
    system.streamers = [streamer]

    data = RaidUpdate(
        id="019fa911-8a8e-7039-a655-76575f0c3f9f",
        target_id="23456",
        target_username="testuser",
        target_display_name="TestUser",
    )

    system.raid_update(streamer.channel_id, data)

    assert streamer.raid == Raid(raid_id=data.id, target_login=data.target_username)
    system.twitch.gql.join_raid.assert_called_once_with(data.id)
    system.event_manager.manage.assert_called_once_with(
        JoinRaid(
            channel_id=streamer.channel_id,
            raid_id=data.id,
            target_username=data.target_username,
        )
    )


def test_moment(system):
    channel_id = "123456"
    moment_id = "019fa914-9384-72ce-a1f3-a2d41249aa9f"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]

    system.moment(channel_id, moment_id)

    system.twitch.gql.claim_moment.assert_called_once_with(moment_id)
    system.event_manager.manage.assert_called_once_with(
        MomentClaim(channel_id=channel_id, moment_id=moment_id)
    )


def test_community_goal_created(system):
    channel_id = "123456"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]

    data = CommunityPointsChannel.CommunityGoalCreated(
        timestamp=datetime.datetime.fromtimestamp(123456789),
        goal=CommunityPointsChannel.Goal(
            id="019fa91f-0ba4-767a-a191-b24e2b28e22a",
            title="test goal",
            is_in_stock=True,
            points_contributed=0,
            goal_amount=1000000,
            per_stream_maximum_user_contribution=2000,
            status="ACTIVE",
        ),
    )

    system.community_goal_created(channel_id, data)

    streamer.update_community_goal.assert_called_once_with(
        CommunityGoal.from_pubsub(data.goal)
    )
    system.twitch.contribute_to_community_goals.assert_called_once_with(streamer)


def test_community_goal_updated(system):
    channel_id = "123456"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]

    data = CommunityPointsChannel.CommunityGoalUpdated(
        timestamp=datetime.datetime.fromtimestamp(123456789),
        goal=CommunityPointsChannel.Goal(
            id="019fa91f-0ba4-767a-a191-b24e2b28e22a",
            title="test goal",
            is_in_stock=True,
            points_contributed=1000,
            goal_amount=1000000,
            per_stream_maximum_user_contribution=2000,
            status="ACTIVE",
        ),
    )

    system.community_goal_updated(channel_id, data)

    streamer.update_community_goal.assert_called_once_with(
        CommunityGoal.from_pubsub(data.goal)
    )
    system.twitch.contribute_to_community_goals.assert_called_once_with(streamer)


def test_community_goal_deleted(system):
    channel_id = "123456"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]

    data = CommunityPointsChannel.CommunityGoalDeleted(
        timestamp=datetime.datetime.fromtimestamp(123456789),
        goal=CommunityPointsChannel.Goal(
            id="019fa91f-0ba4-767a-a191-b24e2b28e22a",
            title="test goal",
            is_in_stock=True,
            points_contributed=10000,
            goal_amount=1000000,
            per_stream_maximum_user_contribution=2000,
            status="CLOSED",
        ),
    )

    system.community_goal_deleted(channel_id, data)

    streamer.delete_community_goal.assert_called_once_with(data.goal.id)


def test_subscription(system):
    channel_id = "123456"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]

    data = UserSubscribed(channel_id=channel_id)

    system.subscription(data)

    system.twitch.check_gift_sub.assert_called_once_with(streamer)


def test_weekly_reward_update(system):
    channel_id = "123456"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]

    data = WeeklyRewards.Notification(
        viewer_id="987654",
        channel_id="123456",
        event_id="019fa94f-4835-7667-acd6-6a54a382c610",
        days_visited_this_week=1,
        accumulated_weeks=1,
        notification_type="PROGRESS",
        current_reward=WeeklyRewards.Reward(
            tier=1,
            channel_points=200,
            badge_set_id="badge-id",
            badge_version="1",
        ),
        event_config=WeeklyRewards.Config(days_required_per_week=1),
    )

    # Normal operation
    system.weekly_reward_update(notification=data)
    system.twitch.update_weekly_reward.assert_called_once_with(streamer, data)

    # Untracked streamer
    data.channel_id = "654321"
    system.weekly_reward_update(notification=data)
    system.twitch.update_weekly_reward.assert_called_once()


def test_watch_streak_recovered(system):
    channel_id = "123456"
    streamer = MagicMock()
    streamer.channel_id = channel_id
    system.streamers = [streamer]

    data = ViewerMilestones.StreakRecovered(channel_id=channel_id)

    # Normal operation
    system.watch_streak_recovered(recovery=data)
    assert len(streamer.watch_streak_missed_stremer) == 0
    system.event_manager.manage.assert_called_once_with(
        WatchStreakRecovery(channel_id=data.channel_id)
    )

    # Untracked streamer
    streams = {"1", "2"}
    streamer.watch_streak_missed_streams = streams
    data.channel_id = "654321"
    system.watch_streak_recovered(recovery=data)
    system.event_manager.manage.assert_called_once()
    assert streamer.watch_streak_missed_streams == streams
