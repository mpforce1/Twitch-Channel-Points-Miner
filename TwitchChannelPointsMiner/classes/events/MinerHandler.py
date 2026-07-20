import logging

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Events import Events, ALL
from TwitchChannelPointsMiner.classes.events.Handler import DispatchHandler

logger = logging.getLogger(__name__)


class MinerHandler(DispatchHandler):
    """Core EventHandler for post-miner event handling."""

    def __init__(self, twitch: Twitch, streamers: list[Streamer]):
        super().__init__()
        self.twitch = twitch
        self.streamers = streamers

    def handles(self) -> Events:
        return ALL
