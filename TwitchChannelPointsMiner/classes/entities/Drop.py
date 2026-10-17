from datetime import datetime

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    TimeBasedDropDetails,
    TimeBasedDropInProgress,
)
from TwitchChannelPointsMiner.utils import percentage


class Drop(object):
    __slots__ = [
        "id",
        "name",
        "benefit",
        "minutes_required",
        "subs_required",
        "has_preconditions_met",
        "current_minutes_watched",
        "drop_instance_id",
        "is_claimed",
        "is_claimable",
        "percentage_progress",
        "end_at",
        "start_at",
        "dt_match",
        "is_printable",
    ]

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
        is_claimed: bool = False
    ):
        self.id = _id
        self.name = name
        self.benefit = ", ".join(set([bf for bf in benefits]))
        self.minutes_required = minutes_required
        self.subs_required = subs_required

        self.has_preconditions_met = None  # [True, False], None we don't know
        self.current_minutes_watched = current_minutes_watched
        self.drop_instance_id = drop_instance_id
        self.is_claimed = is_claimed
        self.is_claimable = False
        self.is_printable = False
        self.percentage_progress = (
            100 * current_minutes_watched / minutes_required if minutes_required != 0 else 0
        )

        self.end_at = end_at
        self.start_at = start_at

    @classmethod
    def from_gql(cls, data: TimeBasedDropDetails | TimeBasedDropInProgress):
        if isinstance(data, TimeBasedDropInProgress):
            instance_id = data.self_edge.drop_instance_id
            minutes_watched = data.self_edge.current_minutes_watched
            is_claimed = data.self_edge.is_claimed
        else:
            instance_id = None
            minutes_watched = 0
            is_claimed = False

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
            is_claimed=is_claimed,
        )

    def update(self, progress: TimeBasedDropInProgress.SelfEdge):
        self.has_preconditions_met = progress.has_preconditions_met

        updated_percentage = percentage(
            progress.current_minutes_watched, self.minutes_required
        )
        quarter = round((updated_percentage / 25), 4).is_integer()
        self.is_printable = (
            # The new currentMinutesWatched are GT than previous
            progress.current_minutes_watched > self.current_minutes_watched
            and (
                # The drop is printable when we have a new updated values and:
                #  - also the percentage It's different and  quarter is True (self.current_minutes_watched != 0 for skip boostrap phase)
                #  - or we have watched 1 and the previous value is 0 - We are collecting a new drop :)
                (
                    updated_percentage > self.percentage_progress
                    and quarter is True
                    and self.current_minutes_watched != 0
                )
                or (
                    progress.current_minutes_watched == 1
                    and self.current_minutes_watched == 0
                )
            )
        )

        self.current_minutes_watched = progress.current_minutes_watched
        self.drop_instance_id = progress.drop_instance_id
        self.is_claimed = progress.is_claimed
        self.is_claimable = (
            self.is_claimed is False and self.drop_instance_id is not None and self.subs_required == 0
        )
        self.percentage_progress = updated_percentage

    def __repr__(self):
        return f"Drop(id={self.id}, name={self.name}, benefit={self.benefit}, minutes_required={self.minutes_required}, has_preconditions_met={self.has_preconditions_met}, current_minutes_watched={self.current_minutes_watched}, percentage_progress={self.percentage_progress}%, drop_instance_id={self.drop_instance_id}, is_claimed={self.is_claimed})"

    def __str__(self):
        return (
            f"{self.name} ({self.benefit}) {self.current_minutes_watched}/{self.minutes_required} ({self.percentage_progress}%)"
            if Settings.logger.less
            else self.__repr__()
        )

    def progress_bar(self):
        progress = self.percentage_progress // 2
        remaining = (100 - self.percentage_progress) // 2
        if remaining + progress < 50:
            remaining += 50 - (remaining + progress)
        return f"|{('█' * progress)}{(' ' * remaining)}|\t{self.percentage_progress}% [{self.current_minutes_watched}/{self.minutes_required}]"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        else:
            return False

    def is_progressable(self):
        """True if this Drop's percentage progress can be progressed by the miner, False otherwise."""
        return self.is_claimable and self.percentage_progress < 100
