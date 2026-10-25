from datetime import datetime

import pytest

from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.Drop import Drop

test_progress_bar_data = [
    (0, 0, 10, "|          |\t0.00% [0/0]"),
    (0, 15, 10, "|          |\t0.00% [0/15]"),
    (1, 15, 10, "|          |\t6.67% [1/15]"),
    (2, 15, 10, "|█         |\t13.33% [2/15]"),
    (5, 15, 10, "|███       |\t33.33% [5/15]"),
    (7, 15, 10, "|████      |\t46.67% [7/15]"),
    (10, 15, 10, "|██████    |\t66.67% [10/15]"),
    (14, 15, 10, "|█████████ |\t93.33% [14/15]"),
    (15, 15, 10, "|██████████|\t100.00% [15/15]"),
]


@pytest.mark.parametrize("current,required,segments,expected", test_progress_bar_data)
def test_progress_bar(current: int, required: int, segments: int, expected: str):
    drop = Drop(
        _id="01a16969-af68-741d-bd14-1c7ffd60e359",
        name="Campaign Name",
        end_at=datetime.now(),
        start_at=datetime.now(),
        benefits=[],
        subs_required=0,
        minutes_required=required,
        current_minutes_watched=current,
    )
    assert drop.progress_bar(segments) == expected
