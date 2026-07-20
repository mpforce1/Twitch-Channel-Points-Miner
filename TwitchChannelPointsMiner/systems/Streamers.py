import datetime
import logging

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
    ViewerMilestones,
    WeeklyRewards,
)
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

    def points_earned(
        self,
        channel_id: str,
        timestamp: datetime.datetime,
        amount: int,
        balance: int,
        reason: str,
    ):
        streamer = find_streamer(self.streamers, channel_id)
        self._update_points_change(streamer, balance, reason)
        self.event_manager.manage(
            gain_for(
                timestamp=timestamp,
                reason=reason,
                channel_id=channel_id,
                amount=amount,
                balance=balance,
            )
        )

    def points_spent(self, channel_id: str, timestamp: datetime.datetime, balance: int):
        streamer = find_streamer(self.streamers, channel_id)
        # We have to estimate this as Twitch doesn't give us the amount in the WS message
        spent_estimate = streamer.channel_points - balance
        self._update_points_change(streamer, balance, "Spent")
        self.event_manager.manage(
            PointsSpent(
                timestamp=timestamp,
                channel_id=channel_id,
                amount=spent_estimate,
                balance=balance,
            )
        )

    def claim_available(
        self, channel_id: str, timestamp: datetime.datetime, claim_id: str
    ):
        self.event_manager.manage(
            BonusPointsAvailable(
                timestamp=timestamp,
                channel_id=channel_id,
                claim_id=claim_id,
            )
        )

    # Raids
    def raid_update(self, channel_id: str, raid: Raid):
        """
        Attempts to join the given Raid if not already joined.
        :param channel_id: The id of the raiding Streamer.
        :param raid: The Raid data.
        """
        streamer = find_streamer(self.streamers, channel_id)
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
    def community_goal_created(self, channel_id: str, data: dict):
        streamer = find_streamer(self.streamers, channel_id)
        # TODO Untested, hard to find this happening live
        streamer.update_community_goal(CommunityGoal.from_pubsub(data))
        self.twitch.contribute_to_community_goals(streamer)

    def community_goal_updated(self, channel_id: str, data: dict):
        streamer = find_streamer(self.streamers, channel_id)
        streamer.update_community_goal(CommunityGoal.from_pubsub(data))
        self.twitch.contribute_to_community_goals(streamer)

    def community_goal_deleted(self, channel_id: str, data: dict):
        streamer = find_streamer(self.streamers, channel_id)
        # TODO Untested, not sure what the message format for this is,
        #      https://github.com/sammwyy/twitch-ps/blob/master/main.js#L417
        #      suggests that it should be just the entire, now deleted, goal model
        streamer.delete_community_goal(data["id"])

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
        for streamer in self.streamers:
            if streamer.channel_id == recovery.channel_id:
                logger.info(f"Watch Streak recovered for {streamer}")
                streamer.watch_streak_missed_streams = set()
                self.event_manager.manage(
                    WatchStreakRecovery(channel_id=recovery.channel_id)
                )
                break
