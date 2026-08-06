import time

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import (
    StreamDown,
    StreamUp,
    StreamViewCount,
)
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.utils.Entities import find_streamer


class StreamSystem:
    def __init__(
        self, twitch: Twitch, streamers: list[Streamer], event_manager: EventManager
    ):
        self.twitch = twitch
        self.streamers = streamers
        self.event_manager = event_manager

    def bring_up(self, channel_id: str):
        """
        Sets the Stream of the Streamer with the given id to up.
        :param channel_id: The id of the Streamer
        """
        streamer = find_streamer(self.streamers, channel_id)
        streamer.stream_up = time.time()
        self.event_manager.manage(StreamUp(streamer=streamer))

    def bring_down(self, channel_id: str):
        """
        Sets the Stream of the Streamer with the given id to down.
        :param channel_id: The id of the Streamer.
        """
        streamer = find_streamer(self.streamers, channel_id)
        if streamer.is_online:
            streamer.set_offline()
            self.event_manager.manage(StreamDown(streamer=streamer))

    def update_view_count(self, channel_id: str, view_count: int):
        """
        Updates the view count of the Stream of the Streamer with the given id.
        :param channel_id: The id of the Streamer.
        :param view_count: The current view count.
        """
        streamer = find_streamer(self.streamers, channel_id)
        if streamer.stream_up_elapsed():
            self.twitch.check_streamer_online(streamer)
        self.event_manager.manage(
            StreamViewCount(streamer=streamer, view_count=view_count)
        )
