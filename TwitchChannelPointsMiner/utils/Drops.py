from datetime import datetime, timezone
from urllib.parse import urlsplit

from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropsCampaign,
    DropsReward,
    DropsRewardGroup,
)


def reward_requires_linking(reward: DropsReward):
    if reward.account_link_url is None or reward.account_link_url.strip() == "":
        return False
    hostname = urlsplit(reward.account_link_url).hostname
    # Assume we require linking if there's no host
    return not "twitch.tv" in hostname if hostname is not None else True


def is_reward_group_progressable(group: DropsRewardGroup, allow_unlinked: bool) -> bool:
    # Filter rewards that aren't linked
    if not allow_unlinked:
        rewards = [
            reward
            for reward in group.rewards
            if not reward_requires_linking(reward) or reward.is_account_connected
        ]
    else:
        rewards = group.rewards
    # Filter groups with no rewards
    if len(rewards) <= 0:
        return False
    requirements = group.progress_criteria.requirements
    # Filter groups with a turbo sub requirement
    if requirements.turbo_subs > 0:
        return False
    if group.self_edge is None:
        current_subs = 0
        current_minutes_watched = 0
        status = None
    else:
        current_subs = group.self_edge.current_subs
        current_minutes_watched = group.self_edge.current_minutes_watched
        status = group.self_edge.status
    # Filter groups with a higher sub requirement than the user has
    if requirements.subs > current_subs:
        return False
    # Filter groups with more minutes watched than required
    if current_minutes_watched >= requirements.minutes_watched:
        return False
    # Filter groups that are already claimable/claimed
    if status in {"CLAIMABLE", "CLAIMED"}:
        return False
    # Filter track and lane type groups
    # Track and lane type groups allow you to progress a reward track down a user selected lane
    # If the user has selected a lane, we can automatically progress it
    if group.track is not None and group.lane is not None:
        if group.self_edge is None:
            # No self indicates this is not the selection
            return False
        if group.self_edge.current_window is None:
            # No window indicates this is not the selection
            return False
        if group.self_edge.current_window.expires_at < datetime.now(timezone.utc):
            # The track window is over
            return False
    return True


def is_campaign_progressable(campaign: DropsCampaign, allow_unlinked: bool) -> bool:
    if campaign.end_at < datetime.now(timezone.utc):
        return False
    reward_groups = [
        group
        for group in campaign.reward_groups
        if is_reward_group_progressable(group, allow_unlinked=allow_unlinked)
    ]
    if len(reward_groups) == 0:
        return False
    return True
