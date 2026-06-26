import datetime
from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.utils.Utils import simple_repr


class Gifter:
    def __init__(self, _id: str, username: str, display_name: str):
        self.id = _id
        self.username = username
        self.display_name = display_name

    def __repr__(self):
        return simple_repr(self)


class Target:
    def __init__(self, _id: str, username: str, display_name: str):
        self.id = _id
        self.username = username
        self.display_name = display_name

    def __repr__(self):
        return simple_repr(self)


class GiftSub:
    def __init__(
        self,
        _id: str,
        target: Target,
        gifter: Gifter | None,
        tier: int,
        ends_at: datetime.datetime,
    ):
        self.id = _id
        self.target = target
        self.gifter = gifter
        self.tier = tier
        self.ends_at = ends_at

    def __repr__(self):
        return simple_repr(self)

    def describe(self) -> str:
        ends_at = self.ends_at.astimezone(datetime.datetime.now().tzinfo)
        days = (self.ends_at - datetime.datetime.now(tz=datetime.timezone.utc)).days
        days_plural = "day" if days == 1 else "days"
        gifter = (
            Settings.logger.anonymiser.username(self.gifter.display_name)
            if self.gifter is not None
            else "Anonymous"
        )
        target = Settings.logger.anonymiser.username(self.target.display_name)
        return f"Tier-{self.tier} Gift Sub from {gifter} for {target}, ends at {ends_at} (in {days} {days_plural})"

    def __eq__(self, other):
        if not isinstance(other, GiftSub):
            return False
        return other.id == self.id
