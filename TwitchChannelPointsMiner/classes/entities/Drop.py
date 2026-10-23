import math
from datetime import datetime

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropsRewardGroup,
    TimeBasedDropInProgress,
)
from TwitchChannelPointsMiner.classes.websocket.data.UserDropEvents import DropProgress


class Drop:
    def __init__(
        self,
        _id: str,
        name: str,
        benefits: list[str],
        minutes_required: int,
        subs_required: int,
        end_at: datetime,
        start_at: datetime,
        drop_instance_id: str | None = None,
        current_minutes_watched: int = 0,
        current_subs: int = 0,
        is_claimed: bool = False,
    ):
        self.id = _id
        self.name = name
        self.benefit = ", ".join(set([bf for bf in benefits]))
        self.minutes_required = minutes_required
        self.subs_required = subs_required

        self.has_preconditions_met = None  # [True, False], None we don't know
        self.current_minutes_watched = current_minutes_watched
        self.current_subs = current_subs
        self.drop_instance_id = drop_instance_id
        self.is_claimed = is_claimed
        self.is_claimable = (
            self.is_claimed is False
            and self.drop_instance_id is not None
            and self.subs_required == 0
        )
        self.percentage_progress: float = (
            100 * current_minutes_watched / minutes_required
            if minutes_required != 0
            else 0
        )

        self.end_at = end_at
        self.start_at = start_at

    @classmethod
    def from_gql(cls, data: TimeBasedDropInProgress):
        instance_id = data.self_edge.drop_instance_id
        minutes_watched = data.self_edge.current_minutes_watched
        is_claimed = data.self_edge.is_claimed

        return cls(
            _id=data.id,
            name=data.name,
            benefits=[bf for bf in data.benefits],
            minutes_required=data.required_minutes_watched,
            subs_required=data.required_subs,
            end_at=data.end_at,
            start_at=data.start_at,
            drop_instance_id=instance_id,
            current_minutes_watched=minutes_watched,
            current_subs=data.self_edge.current_subs,
            is_claimed=is_claimed,
        )

    @classmethod
    def from_gql_reward_group(
        cls, data: DropsRewardGroup, end_at: datetime, start_at: datetime
    ):
        self_edge = data.self_edge
        if self_edge is not None:
            minutes_watched = self_edge.current_minutes_watched
            subs = self_edge.current_subs
        else:
            minutes_watched = 0
            subs = 0
        return cls(
            _id=data.id,
            name=data.name,
            benefits=[reward.name for reward in data.rewards],
            minutes_required=data.progress_criteria.requirements.minutes_watched,
            subs_required=data.progress_criteria.requirements.subs,
            end_at=end_at,
            start_at=start_at,
            drop_instance_id=None,  # We can't get this info at the reward group stage
            current_minutes_watched=minutes_watched,
            current_subs=subs,
            is_claimed=False,
        )

    def _update_percentage(self):
        self.percentage_progress = (
            self.current_minutes_watched / self.minutes_required
            if self.minutes_required != 0
            else 0
        )

    def update(self, progress: TimeBasedDropInProgress):
        self.has_preconditions_met = progress.self_edge.has_preconditions_met
        self.current_minutes_watched = progress.self_edge.current_minutes_watched
        self.current_subs = progress.self_edge.current_subs
        self.drop_instance_id = progress.self_edge.drop_instance_id
        self.is_claimed = progress.self_edge.is_claimed
        self.is_claimable = (
            self.is_claimed is False
            and self.drop_instance_id is not None
            and self.subs_required == 0
        )
        self._update_percentage()

    def update_progress(self, progress: DropProgress):
        self.current_minutes_watched = progress.current_progress_min
        self.minutes_required = progress.required_progress_min
        self._update_percentage()

    def __repr__(self):
        return f"Drop(id={self.id}, name={self.name}, benefit={self.benefit}, minutes_required={self.minutes_required}, has_preconditions_met={self.has_preconditions_met}, current_minutes_watched={self.current_minutes_watched}, percentage_progress={self.percentage_progress}%, drop_instance_id={self.drop_instance_id}, is_claimed={self.is_claimed})"

    def __str__(self):
        return (
            f"{self.name} ({self.benefit}) {self.current_minutes_watched}/{self.minutes_required} ({self.percentage_progress}%)"
            if Settings.logger.less
            else self.__repr__()
        )

    def progress_bar(self, segments: int = 10):
        progress = math.floor(self.percentage_progress * segments)
        remaining = segments - progress
        return f"|{('█' * progress)}{(' ' * remaining)}|\t{self.percentage_progress * 100:.2f}% [{self.current_minutes_watched}/{self.minutes_required}]"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        else:
            return False

    def has_enough_subs(self):
        """Returns True if this Drop has enough subs to meet the sub requirement."""
        return self.current_subs >= self.subs_required

    def meets_base_requirements(self):
        """Returns True if this Drop has met its base requirements (subs)."""
        return self.has_enough_subs()

    def has_enough_minutes(self):
        """Returns True if this Drop has accumulated enough minutes watched to meet the minutes watched requirement."""
        return self.current_minutes_watched >= self.minutes_required

    def is_progressable(self):
        """True if this Drop's percentage progress can be progressed by the miner."""
        return (
            # Can't already be claimed
            not self.is_claimed
            # Can't be currently claimable
            and not self.is_claimable
            # Must have enough subs
            and self.has_enough_subs()
            # Can't have enough minutes
            and not self.has_enough_minutes()
        )

    def completed(self):
        """
        Returns True if this Drop could have been progressed and has enough minutes.
        """
        return self.meets_base_requirements() and self.has_enough_minutes()
