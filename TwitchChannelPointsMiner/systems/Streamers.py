import logging

from TwitchChannelPointsMiner.classes.Anonymiser import Anonymiser
from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.CommunityGoal import CommunityGoal
from TwitchChannelPointsMiner.classes.entities.Raid import Raid
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import (
    BonusPointsAvailable,
    JoinRaid,
    MomentClaim,
    PointsSpent,
    WatchStreakRecovery,
    gain_for,
)
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.gql.Errors import RetryError
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
from TwitchChannelPointsMiner.utils.Entities import find_streamer

logger = logging.getLogger(__name__)


class StreamerSystem:
    def __init__(
        self, twitch: Twitch, streamers: list[Streamer], event_manager: EventManager
    ):
        self.twitch = twitch
        self.streamers = streamers
        self.event_manager = event_manager

    # Channel Points
    def _update_points_change(self, streamer: Streamer, balance: int, reason: str):
        streamer.channel_points = balance
        if Settings.enable_analytics is True:
            streamer.persistent_series(event_type=reason)

    def points_earned(self, data: CommunityPointsUser.PointsEarned):
        streamer = find_streamer(self.streamers, data.channel_id)
        self._update_points_change(streamer, data.balance, data.reason)
        self.event_manager.manage(
            gain_for(
                timestamp=data.timestamp,
                reason=data.reason,
                channel_id=data.channel_id,
                amount=data.amount,
                balance=data.balance,
            )
        )

    def points_spent(self, data: CommunityPointsUser.PointsSpent):
        streamer = find_streamer(self.streamers, data.channel_id)
        # We have to estimate this as Twitch doesn't give us the amount in the WS message
        spent_estimate = streamer.channel_points - data.balance
        self._update_points_change(streamer, data.balance, "Spent")
        self.event_manager.manage(
            PointsSpent(
                timestamp=data.timestamp,
                channel_id=data.channel_id,
                amount=spent_estimate,
                balance=data.balance,
            )
        )

    def claim_available(self, data: CommunityPointsUser.ClaimAvailable):
        self.event_manager.manage(
            BonusPointsAvailable(
                timestamp=data.timestamp,
                channel_id=data.channel_id,
                claim_id=data.claim_id,
                amount=data.amount,
            )
        )

    # Raids
    def raid_update(self, channel_id: str, data: RaidUpdate):
        """
        Attempts to join the given Raid if not already joined.
        :param channel_id: The id of the raiding Streamer.
        :param data: The update.
        """
        streamer = find_streamer(self.streamers, channel_id)
        raid = Raid(raid_id=data.id, target_login=data.target_username)
        if streamer.raid != raid:
            streamer.raid = raid
            target = Settings.logger.anonymiser.username(raid.target_login)
            try:
                self.twitch.gql.join_raid(raid.raid_id)
                logger.info(f"Joining raid from {streamer} to {target}!")
            except RetryError as e:
                logger.error(f"Error joining raid from {streamer} to {target}: {e}")
                return

            self.event_manager.manage(
                JoinRaid(
                    channel_id=channel_id,
                    raid_id=raid.raid_id,
                    target_username=raid.target_login,
                )
            )

    # Moments
    def moment(self, channel_id: str, moment_id: str):
        streamer = find_streamer(self.streamers, channel_id)
        if Settings.logger.less is False:
            logger.info(f"Claiming the moment for {streamer}!")
        try:
            self.twitch.gql.claim_moment(moment_id)
        except RetryError as e:
            logger.error(
                f"Error while trying to claim moment with id {moment_id} for {Settings.logger.anonymiser.streamer_username(streamer)}: {e}",
            )
            return

        self.event_manager.manage(
            MomentClaim(channel_id=channel_id, moment_id=moment_id)
        )

    # Community Goals
    def community_goal_created(
        self, channel_id: str, data: CommunityPointsChannel.CommunityGoalCreated
    ):
        streamer = find_streamer(self.streamers, channel_id)
        # TODO Untested, hard to find this happening live
        streamer.update_community_goal(CommunityGoal.from_pubsub(data.goal))
        self.twitch.contribute_to_community_goals(streamer)

    def community_goal_updated(
        self, channel_id: str, data: CommunityPointsChannel.CommunityGoalUpdated
    ):
        streamer = find_streamer(self.streamers, channel_id)
        streamer.update_community_goal(CommunityGoal.from_pubsub(data.goal))
        self.twitch.contribute_to_community_goals(streamer)

    def community_goal_deleted(
        self, channel_id: str, data: CommunityPointsChannel.CommunityGoalDeleted
    ):
        streamer = find_streamer(self.streamers, channel_id)
        # TODO Untested, not sure what the message format for this is,
        #      https://github.com/sammwyy/twitch-ps/blob/master/main.js#L417
        #      suggests that it should be just the entire, now deleted, goal model
        streamer.delete_community_goal(data.goal.id)

    # Subscriptions
    def subscription(self, notification: UserSubscribed):
        try:
            streamer = find_streamer(self.streamers, notification.channel_id)
            self.twitch.check_gift_sub(streamer)
        except KeyError:
            logger.debug(
                f"Received subscription notification for non-miner channel: {Settings.logger.anonymiser.channel_id(notification.channel_id)}"
            )

    # Weekly Rewards
    def weekly_reward_update(self, notification: WeeklyRewards.Notification):
        try:
            streamer = find_streamer(self.streamers, notification.channel_id)
            self.twitch.update_weekly_reward(streamer, notification)
        except KeyError:
            logger.debug(
                f"Received weekly rewards notification for non-miner channel: {Settings.logger.anonymiser.channel_id(notification.channel_id)}"
            )

    # Watch Streak Milestones
    def watch_streak_recovered(self, recovery: ViewerMilestones.StreakRecovered):
        try:
            streamer = find_streamer(self.streamers, recovery.channel_id)
            logger.info(f"Watch Streak recovered for {streamer}")
            streamer.watch_streak_missed_streams = set()
            self.event_manager.manage(
                WatchStreakRecovery(channel_id=recovery.channel_id)
            )
        except KeyError:
            logger.debug(
                f"Watch Streak Recovery for non-miner channel: {Settings.logger.anonymiser.channel_id(recovery.channel_id)}"
            )
