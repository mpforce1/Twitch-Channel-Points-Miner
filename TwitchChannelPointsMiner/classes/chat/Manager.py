import logging
import time
from threading import Lock, Thread
from typing import Literal, Protocol

from irc.bot import SingleServerIRCBot

from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.ClientSession import ClientSession
from TwitchChannelPointsMiner.classes.Settings import Events, Settings
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import ChatMention
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.constants import IRC, IRC_PORT
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep

logger = logging.getLogger(__name__)


ClientIRCState = Literal[
    "uninitialised", "unwelcomed", "welcomed", "reconnecting", "done"
]


class ClientIRC(SingleServerIRCBot):
    def __init__(
        self, event_manager: EventManager, username: str, token: str, channel: Streamer
    ):
        self.event_manager = event_manager
        self.token = token
        self.streamer = channel
        self.channel = "#" + channel.username
        self.state: ClientIRCState = "uninitialised"

        super(ClientIRC, self).__init__(
            [(IRC, IRC_PORT, f"oauth:{token}")], username, username
        )

    def on_welcome(self, client, event):
        # Only info log during reconnects, debug otherwise
        log_type = (
            logger.info if self.state in {"welcomed", "reconnecting"} else logger.debug
        )
        log_type(f"ClientIRC: {self.streamer}: connected")
        self.state = "welcomed"
        client.join(self.channel)

    def _on_disconnect(self, connection, event):
        # Debug log if this is a planned disconnect, info otherwise
        if self.state != "done":
            self.state = "reconnecting"
            log_type = logger.info
        else:
            log_type = logger.debug
        log_type(f"ClientIRC: {self.streamer}: disconnected")
        super()._on_disconnect(connection, event)

    def start(self):
        self._connect()
        self.state = "unwelcomed"
        while self.state != "done":
            try:
                self.reactor.process_once(timeout=0.2)
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"Exception raised: {e}. State: {self.state}")

    def die(self, msg="Bye, cruel world!"):
        # Set to done and allow time for the main thread to stop
        self.state = "done"
        time.sleep(0.3)
        self.connection.disconnect(msg)

    # """
    def on_pubmsg(self, connection, event):
        msg = event.arguments[0]
        mention = None

        if Settings.disable_at_in_nickname is True:
            mention = f"{self._nickname.lower()}"
        else:
            mention = f"@{self._nickname.lower()}"

        # also self._realname
        # if msg.startswith(f"@{self._nickname}"):
        if mention != None and mention in msg.lower():
            # nickname!username@nickname.tmi.twitch.tv
            nick = event.source.split("!", 1)[0]
            # chan = event.target

            if Settings.logger.anonymiser.strict:
                msg = "REDACTED"

            logger.info(
                f"{Settings.logger.anonymiser.username(nick)} at {Settings.logger.anonymiser.username(self.channel)} wrote: {msg}",
                extra={"emoji": ":speech_balloon:", "event": Events.CHAT_MENTION},
            )
            self.event_manager.manage(
                ChatMention(streamer=self.streamer, actor=nick, message=msg)
            )


class ThreadChat(Thread):
    def __deepcopy__(self, memo):
        return None

    def __init__(
        self, event_manager: EventManager, username: str, token: str, channel: Streamer
    ):
        super(ThreadChat, self).__init__(
            name=f"ThreadChat#{channel.channel_id}", daemon=True
        )

        self.event_manager = event_manager
        self.username = username
        self.token = token
        self.channel = channel

        self.chat_irc = None
        self.running = True
        self._lock = Lock()

    def connected(self) -> bool:
        return self.chat_irc is not None

    def disconnect(self):
        """
        Disconnects the client.
        """
        with self._lock:
            if self.chat_irc is not None:
                logger.info(
                    f"Leave IRC Chat: {Settings.logger.anonymiser.username(self.channel.username)}",
                    extra={"emoji": ":speech_balloon:"},
                )
                # Set to none first to prevent `run` calling `start` again
                old_irc = self.chat_irc
                self.chat_irc = None
                old_irc.die()

    def connect(self):
        """
        Connects or reconnects the chat client.
        """
        self.disconnect()
        self.chat_irc = ClientIRC(
            self.event_manager,
            self.username,
            self.token,
            self.channel,
        )
        logger.info(
            f"Join IRC Chat: {Settings.logger.anonymiser.username(self.channel.username)}",
            extra={"emoji": ":speech_balloon:"},
        )

    def run(self):
        while self.running:
            if self.chat_irc is not None:
                try:
                    # The actual run loop happens in here
                    self.chat_irc.start()
                except Exception as e:
                    logger.error(f"Error processing chat for {self.channel}: {e}")
            else:
                interruptible_sleep(lambda: self.running, 0.1)

        # Shutdown
        logger.debug(f"{self.name}: Shutting Down")
        self.disconnect()
        logger.debug(f"{self.name}: Shut Down")

    def stop(self):
        """
        Stops this thread by setting its `running` flag to False, the Thread should shut down soon after.
        """
        self.running = False
        self.disconnect()


class ChatManager(Thread):
    """Manages Chat connections for miner Streamers"""

    def __init__(
        self,
        account_username: str,
        streamers: list[Streamer],
        event_manager: EventManager,
        client_session: ClientSession,
    ):
        super().__init__(name="Chat Manager", daemon=True)
        self.account_username = account_username
        self.streamers = streamers
        self.event_manager = event_manager
        self.client_session = client_session
        self.chats = dict[str, ThreadChat]()
        self.running = True

    def process_streamer(self, streamer: Streamer):
        """
        Checks if the streamer's chat should be online/offline then connects/disconnects as required.
        :param streamer: The streamer to process.
        """
        # Get or create the streamer's chat
        chat = self.chats.get(streamer.channel_id, None)
        if chat is None or not chat.is_alive():
            chat = ThreadChat(
                self.event_manager,
                self.account_username,
                self.client_session.login.get_auth_token(),
                streamer,
            )
            chat.start()
            self.chats[streamer.channel_id] = chat
        # Check the state
        match (streamer.settings.chat, chat.connected(), streamer.is_online):
            case (
                (ChatPresence.NEVER, True, _)
                | (ChatPresence.ONLINE, True, False)
                | (ChatPresence.OFFLINE, True, True)
            ):
                chat.disconnect()
            case (
                (ChatPresence.ALWAYS, False, _)
                | (ChatPresence.ONLINE, False, True)
                | (ChatPresence.OFFLINE, False, False)
            ):
                chat.connect()

    def run(self):
        while self.running:
            for streamer in self.streamers:
                try:
                    self.process_streamer(streamer)
                except Exception as e:
                    logger.error(f"Error while processing chat for {streamer}: {e}")

            interruptible_sleep(lambda: self.running, 0.1)

        # Shutdown
        logger.debug(f"{self.name}: Shutting Down")
        for channel_id in self.chats:
            try:
                self.chats[channel_id].stop()
            except Exception as e:
                logger.error(
                    f"{self.name}: Error while shutting down chat thread for: {e}"
                )
        logger.debug(f"{self.name}: Shut Down")

    def stop(self):
        self.running = False


class ChatManagerFactory(Protocol):
    def __call__(
        self,
        account_username: str,
        streamers: list[Streamer],
        background_tasks: list[Thread],
        event_manager: EventManager,
        client_session: ClientSession,
    ) -> ChatManager: ...


def chat_manager_factory(
    account_username: str,
    streamers: list[Streamer],
    background_tasks: list[Thread],
    event_manager: EventManager,
    client_session: ClientSession,
):
    manager = ChatManager(
        account_username=account_username,
        streamers=streamers,
        event_manager=event_manager,
        client_session=client_session,
    )
    manager.start()
    background_tasks.append(manager)
    return manager
