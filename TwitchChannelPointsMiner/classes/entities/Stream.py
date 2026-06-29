import json
import logging
import time
from base64 import b64encode
from datetime import datetime

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.PlaybackAccessToken import (
    PlaybackAccessToken,
)
from TwitchChannelPointsMiner.classes.gql import Tag
from TwitchChannelPointsMiner.classes.gql.data.response.BroadcastSettings import (
    GameBroadcastSettings,
)
from TwitchChannelPointsMiner.classes.gql.data.response.RewardList import (
    WatchStreakMilestone,
)
from TwitchChannelPointsMiner.constants import DROP_ID

logger = logging.getLogger(__name__)


class Stream(object):
    __slots__ = [
        "broadcast_id",
        "title",
        "game",
        "tags",
        "drops_tags",
        "campaigns",
        "campaigns_ids",
        "viewers_count",
        "spade_url",
        "payload",
        "playback_access_token",
        "hls_url",
        "watch_streak_missing",
        "minute_watched",
        "watch_count",
        "__last_update",
        "__minute_watched_timestamp",
        "created_at",
        "watch_session_state",
    ]

    def __init__(self):
        self.broadcast_id = None

        self.title: str | None = None
        self.game: GameBroadcastSettings | None = None
        self.tags: list[Tag] = []

        self.drops_tags: bool = False
        self.campaigns: list[Campaign] = []
        self.campaigns_ids: list[str] = []

        self.viewers_count = 0
        self.__last_update = 0

        self.spade_url: str | None = None
        self.payload = None
        self.playback_access_token: PlaybackAccessToken | None = None
        """A token that allows accessing stream media for this Stream."""
        self.hls_url: str | None = None
        """The URL of the HLS stream playlist for this Stream."""

        self.created_at: datetime | None = None

        # Start as None as we've yet to begin a watch session
        self.watch_session_state: datetime | None = None
        """The start time of the current watch session or None if we haven't started a session since the last WATCH."""

        self.init_watch_streak()

    def encode_payload(self) -> dict:
        json_event = json.dumps(self.payload, separators=(",", ":"))
        return {"data": (b64encode(json_event.encode("utf-8"))).decode("utf-8")}

    def update(
        self,
        broadcast_id: str,
        title: str,
        game: GameBroadcastSettings | None,
        tags: list[Tag],
        viewers_count: int,
        created_at: datetime,
        watch_streak_milestone: WatchStreakMilestone | None,
    ):
        if self.broadcast_id != broadcast_id:
            # Different stream, reset state
            self.init_watch_streak()
            self.playback_access_token = None
            self.hls_url = None

        self.broadcast_id = broadcast_id
        self.title = title.strip()
        self.game = game
        # #343 temporary workaround
        self.tags = tags or []
        # ------------------------
        self.viewers_count = viewers_count
        self.created_at = created_at

        if watch_streak_milestone is not None and self.watch_streak_missing:
            # Don't bother updating if we've already got the streak
            last_streak_achievement_timestamp = (
                watch_streak_milestone.viewer_milestone.achievement_timestamp
            )
            if (
                last_streak_achievement_timestamp is not None
                and last_streak_achievement_timestamp > created_at
            ):
                # We've got a streak going + it was last achieved during this stream
                self.watch_streak_missing = False

        self.drops_tags = (DROP_ID in [tag.id for tag in self.tags]) and (
            self.game is not None
        )
        self.__last_update = time.time()

        logger.debug(f"Update: {self}")

    def __repr__(self):
        return f"Stream(title={self.title}, game={self.__str_game()}, tags={self.__str_tags()}, id={self.broadcast_id}, created_at={self.created_at}, watch_streak_missing={self.watch_streak_missing}, minute_watched={self.minute_watched})"

    def __str__(self):
        return f"{self.title}" if Settings.logger.less else self.__repr__()

    def __str_tags(self):
        return (
            None
            if self.tags == []
            else ", ".join([tag.localized_name for tag in self.tags])
        )

    def __str_game(self):
        return None if self.game is None else self.game.display_name

    def game_name(self):
        return None if self.game is None else self.game.name

    def game_id(self):
        return None if self.game is None else self.game.id

    def update_required(self):
        return self.__last_update == 0 or self.update_elapsed() >= 120

    def update_elapsed(self):
        return 0 if self.__last_update == 0 else (time.time() - self.__last_update)

    def init_watch_streak(self):
        self.watch_streak_missing = True
        self.minute_watched = 0
        self.watch_count = 0
        self.__minute_watched_timestamp = 0

    def update_minute_watched(self):
        if self.__minute_watched_timestamp != 0:
            self.minute_watched += round(
                (time.time() - self.__minute_watched_timestamp) / 60, 5
            )
        self.__minute_watched_timestamp = time.time()
