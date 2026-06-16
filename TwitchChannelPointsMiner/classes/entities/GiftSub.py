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
        self, _id: str, target: Target, gifter: Gifter | None, tier: int, months: int
    ):
        self.id = _id
        self.target = target
        self.gifter = gifter
        self.tier = tier
        self.months = months

    def __repr__(self):
        return simple_repr(self)

    def describe(self) -> str:
        month_plural = "Months" if self.months > 1 else "Month"
        gifter = self.gifter.display_name if self.gifter is not None else "Anonymous"
        return f"{self.months} {month_plural} Tier-{self.tier} Gift Sub from {gifter} for {self.target.display_name}"

    def __eq__(self, other):
        if not isinstance(other, GiftSub):
            return False
        return other.id == self.id
