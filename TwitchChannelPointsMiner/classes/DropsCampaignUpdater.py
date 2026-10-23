import datetime
import logging
from threading import Thread

from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import Error
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.systems.Drops import DropsSystem
from TwitchChannelPointsMiner.classes.systems.Streams import StreamSystem
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep

logger = logging.getLogger(__name__)


class DropsCampaignUpdater(Thread):
    """Thread that periodically updates the campaigns active for each stream."""

    def __init__(
        self,
        streamers: list[Streamer],
        twitch: Twitch,
        stream_system: StreamSystem,
    ):
        super().__init__(name="Drops Campaign Updater", daemon=True)
        self.streamers = streamers
        self.twitch = twitch
        self.stream_system = stream_system

    def run(self):
        while self.twitch.running:
            # Update each streamer's campaign ids
            for streamer in self.streamers:
                self.stream_system.update_campaigns(streamer.channel_id)
                interruptible_sleep(lambda: self.twitch.running, duration=0.1)
                if not self.twitch.running:
                    # end update loop early
                    return
            # run every 5 mins
            interruptible_sleep(
                lambda: self.twitch.running,
                duration=datetime.timedelta(minutes=5).total_seconds(),
            )


class DropsClaimer(Thread):
    """Thread that periodically claims all available drops in the user's inventory."""

    def __init__(
        self, event_manager: EventManager, twitch: Twitch, inventory_system: DropsSystem
    ):
        super().__init__(name="Drops Claimer", daemon=True)
        self.event_manager = event_manager
        self.twitch = twitch
        self.drops_system = inventory_system

    def run(self):
        try:
            while self.twitch.running:
                self.drops_system.claim_all_drops()
                # run every 15 minutes
                interruptible_sleep(
                    lambda: self.twitch.running,
                    duration=datetime.timedelta(minutes=15).total_seconds(),
                )
        except Exception as e:
            logger.error(f"Error in Drops Claimer: {e}")
            self.event_manager.manage(
                Error(
                    context="Drops Claimer", message="Error in Drops Claimer", error=e
                )
            )
