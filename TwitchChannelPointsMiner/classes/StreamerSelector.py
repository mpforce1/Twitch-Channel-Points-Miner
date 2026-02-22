import abc
import logging
import time
from typing import Protocol, Sequence, Callable

from TwitchChannelPointsMiner.classes.Settings import Priority, StreamerSource
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.utils.LimitedSet import LimitedSet

logger = logging.getLogger(__name__)


class StreamerSelector(abc.ABC):
    """Class for selecting streamers from a list."""

    @abc.abstractmethod
    def select(self, streamers: Sequence[Streamer], max_amount: int) -> list[str]:
        """
        Selects streamers from the list.
        :param streamers: The streamers to consider.
        :param max_amount: The maximum amount of streamers to select.
        :return: The selected streamers.
        """
        pass


def priority_order(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    return [streamer.channel_id for streamer in streamers[:max_amount]]


def priority_points(
    streamers: Sequence[Streamer], max_amount: int, descending: bool
) -> list[str]:
    items = [
        {"points": streamer.channel_points, "id": streamer.channel_id}
        for streamer in streamers
    ]
    items = sorted(
        items,
        key=lambda x: x["points"],
        reverse=descending,
    )
    return [item["id"] for item in items][:max_amount]


def priority_points_ascending(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    return priority_points(streamers, max_amount, False)


def priority_points_descending(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    return priority_points(streamers, max_amount, True)


def priority_streak(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    result = []
    for streamer in streamers:
        if len(result) >= max_amount:
            break
        if (
                streamer.settings.watch_streak is True
                and streamer.stream.watch_streak_missing is True
                and (
                streamer.offline_at == 0
                or ((time.time() - streamer.offline_at) // 60) > 30
        )
        ):
            result.append(streamer.channel_id)
    return result


def priority_drops(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    # max_amount can be ignored due to 1 drop limit
    for streamer in streamers:
        if streamer.any_campaign_has_claimable_drop() is True:
            return [streamer.channel_id]
    return []


def priority_subscribed(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    streamers_with_multiplier = [
        streamer for streamer in streamers if streamer.viewer_has_points_multiplier()
    ]
    streamers_with_multiplier = sorted(
        streamers_with_multiplier,
        key=lambda x: x.total_points_multiplier(),
        reverse=True,
    )
    return [streamer.channel_id for streamer in streamers_with_multiplier[:max_amount]]


class PriorityFunction(Protocol):
    def __call__(self, streamers: Sequence[Streamer], max_amount: int) -> list[str]: ...


priority_functions: dict[Priority, PriorityFunction] = {
    Priority.ORDER: priority_order,
    Priority.POINTS_ASCENDING: priority_points_ascending,
    Priority.POINTS_DESCENDING: priority_points_descending,
    Priority.STREAK: priority_streak,
    Priority.DROPS: priority_drops,
    Priority.SUBSCRIBED: priority_subscribed,
}


class PrioritySelector(StreamerSelector):
    """StreamerSelector that considers a given list of Priorities."""

    def __init__(
        self,
        priorities: list[Priority] | None = None,
        priority_function_overrides: dict[Priority, PriorityFunction] | None = None,
    ):
        self.priorities = priorities if priorities is not None else [Priority.STREAK, Priority.DROPS, Priority.ORDER]
        if priority_function_overrides is not None:
            self.priority_functions = {
                priority: priority_function_overrides.get(
                    priority, priority_functions[priority]
                )
                for priority in priority_functions.keys()
            }
        else:
            self.priority_functions = priority_functions

    def select(self, streamers: Sequence[Streamer], max_amount: int) -> list[str]:
        selected = LimitedSet[str](max_amount)
        unselected = {streamer.channel_id: streamer for streamer in streamers}
        for priority in self.priorities:
            if selected.remaining() <= 0 or len(unselected) <= 0:
                break

            if priority in self.priority_functions:
                to_add = self.priority_functions[priority](
                    list(unselected.values()), selected.remaining()
                )
                if not selected.add(*to_add):
                    break
                else:
                    for streamer in selected:
                        unselected.pop(streamer, None)
            else:
                logger.warning(f"Unknown priority {priority}")

        return list(selected)[:max_amount]


def all_filter(streamers: Sequence[Streamer]) -> Sequence[Streamer]:
    """
    Filter that just returns the original sequence.

    :param streamers: The list of streamers to filter.
    :return: The filtered list.
    """
    return streamers


def in_list_filter(filter_streamers: list[str]) -> Callable[[Sequence[Streamer]], Sequence[Streamer]]:
    """
    Returns a filter function that filters out any streamers that aren't in the given list (based on usernames).

    :param filter_streamers: The usernames of Streamers to keep.
    :return: The filter function.
    """

    def sub_filter(streamers: Sequence[Streamer]) -> Sequence[Streamer]:
        streamers_by_usernames = {streamer.username: streamer for streamer in streamers}
        return [
            streamers_by_usernames[streamer_username]
            for streamer_username in filter_streamers
            if streamer_username in streamers_by_usernames
        ]

    return sub_filter


def from_source_filter(filter_source: StreamerSource) -> Callable[[Sequence[Streamer]], Sequence[Streamer]]:
    """
    Returns a filter function that filters out any streamers that aren't sourced in the given way.

    :param filter_source: The source of Streamers to keep.
    :return: The filter function.
    """
    return lambda streamers: [
        streamer
        for streamer in streamers
        if streamer.source == filter_source
    ]


def arbitrary_filter(filter_function: Callable[[Streamer], bool]) -> Callable[[Sequence[Streamer]], Sequence[Streamer]]:
    """
    Filters out any streamers that don't return `True` for the given function.

    :param filter_function: The function to use when filtering, should return `True` to keep the Streamer.
    :return: The filter function.
    """
    return lambda streamers: [
        streamer
        for streamer in streamers
        if filter_function(streamer)
    ]


class PriorityGroupSelector(StreamerSelector):
    """Selects streamers based on the given streamers filter."""

    def __init__(
        self, streamers: list[str] | StreamerSource | Callable[[Streamer], bool] | None, selector: PrioritySelector
    ) -> None:
        self.streamers = streamers
        """
        If `list[str]` selects from only those streamers with the matching usernames.
        
        If `StreamerSource` selects from only streamers sourced in the given way.
        
        If `Callable` selects from only those streamers that, when passed, return `True`.
        
        If `None` selects from all streamers. 
        """
        self.selector = selector
        """ The `PrioritySelector` to use for the given streamers. """

        # Cache filter function now to avoid doing isinstance every time
        self._filter: Callable[[Sequence[Streamer]], Sequence[Streamer]]
        if self.streamers is None:
            # Use all streamers if None
            self._filter = all_filter
        elif isinstance(self.streamers, StreamerSource):
            # Filter streamers to only those from the given source
            self._filter = from_source_filter(self.streamers)
        elif isinstance(self.streamers, Callable):
            # Filter streamers by filter function
            self._filter = arbitrary_filter(self.streamers)
        elif isinstance(self.streamers, list):
            if len(self.streamers) > 0:
                # Filter out streamers that aren't in the list
                self._filter = in_list_filter(self.streamers)
            else:
                # Use all streamers if list is empty
                self._filter = all_filter
        else:
            raise TypeError("Streamers must be one of list[str], StreamerSource, Callable, or None")

    def select(self, streamers: Sequence[Streamer], max_amount: int) -> list[str]:
        sub_streamers = self._filter(streamers)
        selection = self.selector.select(sub_streamers, max_amount)
        return selection[:max_amount]


class NestedSelector(StreamerSelector):
    """Selects streamers using the given selectors in order."""

    def __init__(self, selectors: list[StreamerSelector]) -> None:
        self.selectors = selectors

    def select(self, streamers: Sequence[Streamer], max_amount: int) -> list[str]:
        selected = LimitedSet(max_amount)
        unselected = {streamer.channel_id: streamer for streamer in streamers}
        for selector in self.selectors:
            selection = selector.select(list(unselected.values()), selected.remaining())
            if not selected.add(*selection):
                break
            else:
                for streamer in selected:
                    unselected.pop(streamer, None)
        return list(selected)[:max_amount]


# Custom priority functions


def priority_streak_by_earliest_stream_created_at(
    streamers: Sequence[Streamer], max_amount: int
) -> list[str]:
    """
    Prioritises only streamers that have streaks, ordered by ascending stream.created_at to prioritise streams that came
    online first.
    :param streamers: The streamers to consider.
    :param max_amount: The maximum amount of streamers to select.
    :return: The selected streamer ids.
    """
    ordered = sorted(
        streamers,
        key=lambda streamer: (
            streamer.stream.created_at.timestamp()
            if streamer.stream.created_at is not None
            else 0
        ),
        reverse=False,
    )
    return priority_streak(ordered, max_amount)
