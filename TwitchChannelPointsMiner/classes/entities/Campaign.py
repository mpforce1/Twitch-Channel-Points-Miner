import datetime
from urllib.parse import urlsplit

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropCampaignInProgress,
    DropsCampaign,
    GameDetails,
)


class Campaign:
    def __init__(
        self,
        _id: str,
        game: GameDetails | None,
        name: str,
        status: str,
        end_at: datetime.datetime,
        start_at: datetime.datetime,
        is_account_connected: bool,
        account_link_url: str | None,
        drops: list[Drop],
    ):
        self.id = _id
        self.game = game
        self.name = name
        self.status = status
        self.end_at = end_at
        self.start_at = start_at
        self.is_account_connected = is_account_connected
        self.account_link_url = account_link_url
        self.dt_match = (
            self.start_at < datetime.datetime.now(datetime.timezone.utc) < self.end_at
        )
        self.in_inventory = False
        self.drops = {drop.id: drop for drop in drops}

    @classmethod
    def from_gql_inventory(cls, data: DropCampaignInProgress):
        """Converts Inventory Campaign data to a Campaign"""
        return cls(
            _id=data.id,
            game=data.game,
            name=data.name,
            status=data.status,
            end_at=data.end_at,
            start_at=data.start_at,
            is_account_connected=data.is_account_connected,
            account_link_url=data.account_link_url,
            drops=[Drop.from_gql(drop) for drop in data.time_based_drops],
        )

    @classmethod
    def from_gql_stream(cls, data: DropsCampaign):
        """Converts Stream Campaign data to a Campaign"""
        # Reward groups actually have unique account connections per reward
        # at this point, we can assume that the whole campaign is connected if any are
        is_account_connected = False
        account_link_url = None
        for group in data.reward_groups:
            for reward in group.rewards:
                if reward.is_account_connected:
                    is_account_connected = True
                    account_link_url = reward.account_link_url
                    break
        return cls(
            _id=data.id,
            game=data.game,
            name=data.name,
            status="",  # We don't have the status at this point
            end_at=data.end_at,
            start_at=data.start_at,
            is_account_connected=is_account_connected,
            account_link_url=account_link_url,
            drops=[
                Drop.from_gql_reward_group(drop, data.end_at, data.start_at)
                for drop in data.reward_groups
            ],
        )

    def __repr__(self):
        return f"Campaign(id={self.id}, name={self.name}, game={self.game}, in_inventory={self.in_inventory})"

    def __str__(self):
        return (
            f"{self.name}, Game: {self.game.display_name if self.game is not None else 'General'} - Drops: {len(self.drops)} pcs. - In inventory: {self.in_inventory}"
            if Settings.logger.less
            else self.__repr__()
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        else:
            return False

    def update(self, new_campaign: DropCampaignInProgress):
        # These values could change during the campaign
        self.status = new_campaign.status
        self.is_account_connected = new_campaign.is_account_connected
        self.account_link_url = new_campaign.account_link_url
        # Update each drop
        for new_drop in new_campaign.time_based_drops:
            old_drop = self.drops[new_drop.id]
            old_drop.update(new_drop)

    def any_drop_claimable(self):
        """Returns True if any Drop in the Campaign can be claimed."""
        return any(drop for drop in self.drops.values() if drop.is_claimable)

    def ended(self):
        """Returns True if this Campaign has ended."""
        return self.end_at <= datetime.datetime.now(datetime.timezone.utc)

    def progressable_drops(self):
        return (drop for drop in self.drops.values() if drop.is_progressable())

    def any_drop_progressable(self):
        """Returns True if any Drop in this Campaign can be progressed."""
        return any(self.progressable_drops())

    def requires_account_link(self):
        if self.is_account_connected:
            # Account already linked
            return False
        if self.account_link_url is None or self.account_link_url.strip() == "":
            # No link URL
            return False
        hostname = urlsplit(self.account_link_url).hostname
        # Assume we require linking if there's no host
        return not "twitch.tv" in hostname if hostname is not None else True

    def progressable(self, allow_unlinked: bool):
        """Returns True if this Campaign can be progressed."""
        return (
            # Must not have ended
            not self.ended()
            # If account linking is required, the account must be linked
            and (allow_unlinked or self.is_account_connected)
            # At least 1 drop must be progressable
            and self.any_drop_progressable()
        )

    def current_drop(self, allow_unlinked: bool) -> Drop | None:
        """Returns the current Drop that can be progressed."""
        if allow_unlinked or self.is_account_connected:
            return min(
                (drop for drop in self.drops.values() if drop.is_progressable()),
                key=lambda drop: drop.minutes_required,
                default=None,
            )
        else:
            return None
