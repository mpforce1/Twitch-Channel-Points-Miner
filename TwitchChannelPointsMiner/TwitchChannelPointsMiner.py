# -*- coding: utf-8 -*-

import logging
import os
import random
import signal
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import TwitchChannelPointsMiner.classes.websocket.hermes.data as hermes_data
from TwitchChannelPointsMiner.classes.Chat import ChatPresence, ThreadChat
from TwitchChannelPointsMiner.classes.Exceptions import StreamerDoesNotExistException
from TwitchChannelPointsMiner.classes.PubSub import PubSubHandler
from TwitchChannelPointsMiner.classes.Settings import FollowersOrder, Priority, Settings, StreamerSource
from TwitchChannelPointsMiner.classes.StreamerSelector import (
    StreamerSelector,
    PrioritySelector,
)
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.EventPrediction import EventPrediction
from TwitchChannelPointsMiner.classes.entities.PubsubTopic import PubsubTopic
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    Streamer,
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.gql.Integration import GQLFactory, GQL
from TwitchChannelPointsMiner.classes.websocket import HermesWebSocketPool, PubSubWebSocketPool
from TwitchChannelPointsMiner.constants import HERMES_WEBSOCKET, CLIENT_ID_WEB
from TwitchChannelPointsMiner.logger import LoggerSettings, configure_loggers
from TwitchChannelPointsMiner.utils import (
    millify,
    at_least_one_value_in_settings_is,
    check_versions,
    get_user_agent,
    internet_connection_available,
    set_default_settings,
    AttemptStrategy,
    interruptible_sleep,
)
from TwitchChannelPointsMiner.utils.Utils import interruptible_repeating_task

# Suppress:
#   - chardet.charsetprober - [feed]
#   - chardet.charsetprober - [get_confidence]
#   - requests - [Starting new HTTPS connection (1)]
#   - Flask (werkzeug) logs
#   - irc.client - [process_data]
#   - irc.client - [_dispatcher]
#   - irc.client - [_handle_message]
logging.getLogger("chardet.charsetprober").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("irc.client").setLevel(logging.ERROR)
logging.getLogger("seleniumwire").setLevel(logging.ERROR)
logging.getLogger("websocket").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class TwitchChannelPointsMiner:
    __slots__ = [
        "username",
        "twitch",
        "claim_drops_startup",
        "enable_analytics",
        "disable_ssl_cert_verification",
        "disable_at_in_nickname",
        "streamer_selector",
        "streamers",
        "events_predictions",
        "background_tasks",
        "ws_pool",
        "session_id",
        "running",
        "start_datetime",
        "original_streamers",
        "logs_file",
        "queue_listener",
    ]

    def __init__(
        self,
        username: str,
        password: str = None,
        claim_drops_startup: bool = False,
        enable_analytics: bool = False,
        disable_ssl_cert_verification: bool = False,
        disable_at_in_nickname: bool = False,
        # Settings for logging and selenium as you can see.
        priority: StreamerSelector | list[Priority] | Priority | None = None,
        # This settings will be global shared trought Settings class
        logger_settings: LoggerSettings = LoggerSettings(),
        # Default values for all streamers
        streamer_settings: StreamerSettings = StreamerSettings(),
        # GQL Integration
        gql: GQL | AttemptStrategy | GQLFactory | None = None,
        # True if we want to use the new Hermes WebSocket API
        use_hermes: bool = False,
    ):
        # Validate the user has changed default username and password
        startup_error = None
        if not username:
            startup_error = "No username"
        elif username == "your-twitch-username":
            startup_error = "Username not changed from default"
        elif not password:
            startup_error = "No password"
        elif password == "write-your-secure-psw":
            startup_error = "Password not changed from default"

        if startup_error is not None:
            logger.error("Please edit your configuration file (run.py) and try again.")
            logger.error(f"{startup_error}, exiting...")
            sys.exit(0)

        # This disables certificate verification and allows the connection to proceed, but also makes it vulnerable to man-in-the-middle (MITM) attacks.
        Settings.disable_ssl_cert_verification = disable_ssl_cert_verification

        Settings.disable_at_in_nickname = disable_at_in_nickname

        Settings.use_hermes = use_hermes

        # Wait for Twitch.tv connectivity with a timeout to avoid hanging forever
        error_printed = False
        connectivity_interval = 5
        connectivity_timeout = 60
        connectivity_start = time.time()
        while not internet_connection_available(host="twitch.tv", port=443):
            if not error_printed:
                logger.error("Waiting for Twitch.tv connectivity...")
                error_printed = True
            if (time.time() - connectivity_start) >= connectivity_timeout:
                logger.error("Unable to reach Twitch.tv after 60 seconds, exiting...")
                sys.exit(0)
            time.sleep(connectivity_interval)

        # Analytics switch
        Settings.enable_analytics = enable_analytics

        if enable_analytics is True:
            Settings.analytics_path = os.path.join(
                Path().absolute(), "analytics", username
            )
            Path(Settings.analytics_path).mkdir(parents=True, exist_ok=True)

        self.username = username

        # Set as global config
        Settings.logger = logger_settings

        # Init as default all the missing values
        streamer_settings.default()
        streamer_settings.bet.default()
        Settings.streamer_settings = streamer_settings

        # user_agent = get_user_agent("FIREFOX")
        user_agent = get_user_agent("CHROME")

        if gql is None:
            # Use the default factory
            gql = GQLFactory()
        elif isinstance(gql, AttemptStrategy):
            # Convenience for the expected most common use case where gql is provided
            gql = GQLFactory(attempt_strategy=gql)
        elif not isinstance(gql, GQLFactory):
            # Invalid argument type
            raise ValueError(f"gql must be an instance of be one of None, AttemptStrategy, or GQLFactory")

        self.twitch = Twitch(self.username, user_agent, password, gql_factory=gql)

        self.claim_drops_startup = claim_drops_startup

        # Convert priority setting into a StreamerSelector
        if priority is None:
            self.streamer_selector = PrioritySelector([Priority.STREAK, Priority.DROPS, Priority.ORDER])
        elif isinstance(priority, Priority):
            self.streamer_selector = PrioritySelector([priority])
        elif isinstance(priority, StreamerSelector):
            self.streamer_selector = priority
        else:
            self.streamer_selector = PrioritySelector(priority)

        self.streamers: list[Streamer] = []
        self.events_predictions: dict[str, EventPrediction] = {}
        self.background_tasks: list[threading.Thread] = []
        self.ws_pool = None

        self.session_id = str(uuid.uuid4())
        self.running = False
        self.start_datetime = None
        self.original_streamers = []

        self.logs_file, self.queue_listener = configure_loggers(
            self.username, logger_settings
        )

        # Check for the latest version of the script
        current_version, github_version = check_versions()

        logger.info(
            f"Twitch Channel Points Miner-{current_version} (fork by mpforce1)"
        )
        logger.info("https://github.com/mpforce1/Twitch-Channel-Points-Miner")

        if github_version == "0.0.0":
            logger.error(
                "Unable to detect if you have the latest version of this script"
            )
        elif current_version != github_version:
            logger.info(f"You are running version {current_version} of this script")
            logger.info(f"The latest version on GitHub is {github_version}")

        for sign in [signal.SIGINT, signal.SIGSEGV, signal.SIGTERM]:
            signal.signal(sign, self.end_signal)

    def analytics(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        refresh: int = 5,
        days_ago: int = 7,
    ):
        # Analytics switch
        if Settings.enable_analytics is True:
            from TwitchChannelPointsMiner.classes.AnalyticsServer import AnalyticsServer

            days_ago = days_ago if days_ago <= 365 * 15 else 365 * 15
            http_server = AnalyticsServer(
                host=host,
                port=port,
                refresh=refresh,
                days_ago=days_ago,
                username=self.username,
            )
            http_server.daemon = True
            http_server.name = "Analytics Thread"
            http_server.start()
        else:
            logger.error("Can't start analytics(), please set enable_analytics=True")

    def mine(
        self,
        streamers: list[Streamer | str] | None = None,
        blacklist: list[str] | None = None,
        followers: bool = False,
        followers_order: FollowersOrder = FollowersOrder.ASC,
    ):
        self.run(
            streamers=streamers,
            blacklist=blacklist,
            followers=followers,
            followers_order=followers_order,
        )

    def run(
        self,
        streamers: list[Streamer | str] | None = None,
        blacklist: list[str] | None = None,
        followers: bool = False,
        followers_order: FollowersOrder = FollowersOrder.ASC,
    ):
        if self.running:
            logger.error("You can't start multiple sessions of this instance!")
            return

        streamers_input = list(streamers) if streamers is not None else []
        blacklist_input = list(blacklist) if blacklist is not None else []

        logger.info(f"Start session: '{self.session_id}'", extra={"emoji": ":bomb:"})
        self.running = True
        self.start_datetime = datetime.now()

        try:
            self.twitch.login()

            if self.claim_drops_startup is True:
                self.twitch.claim_all_drops_from_inventory()

            def normalize_login(name: str) -> str:
                return name.lower().strip().replace(" ", "")

            streamers_pre_loaded: list[tuple[str, StreamerSource]] = []
            streamers_dict: dict[str, str | Streamer] = {}

            for streamer in streamers_input:
                username = (
                    normalize_login(streamer.username)
                    if isinstance(streamer, Streamer)
                    else normalize_login(str(streamer))
                )
                if username not in blacklist_input:
                    streamers_pre_loaded.append((username, StreamerSource.Streamers))
                    streamers_dict[username] = streamer

            if followers is True:
                followers_array = self.twitch.get_followers(order=followers_order)
                logger.info(
                    f"Load {len(followers_array)} followers from your profile!",
                    extra={"emoji": ":clipboard:"},
                )
                for username in followers_array:
                    if (
                        username not in streamers_dict
                        and normalize_login(username) not in blacklist_input
                    ):
                        norm = normalize_login(username)
                        streamers_pre_loaded.append((norm, StreamerSource.Followers))
                        streamers_dict[norm] = norm

            logger.info(
                f"Loading data for {len(streamers_pre_loaded)} streamers. Please wait...",
                extra={"emoji": ":nerd_face:"},
            )
            load_workers = max(1, min(10, len(streamers_pre_loaded))) if streamers_pre_loaded else 0

            def build_streamer(username: str, source: StreamerSource):
                streamer_obj = streamers_dict[username]
                streamer: Streamer = (
                    streamer_obj
                    if isinstance(streamer_obj, Streamer)
                    else Streamer(username)
                )
                streamer.source = source
                streamer.channel_id = self.twitch.get_channel_id(username)
                streamer.settings = set_default_settings(
                    streamer.settings, Settings.streamer_settings
                )
                streamer.settings.bet = set_default_settings(
                    streamer.settings.bet, Settings.streamer_settings.bet
                )
                if streamer.settings.chat != ChatPresence.NEVER:
                    streamer.irc_chat = ThreadChat(
                        self.username,
                        self.twitch.client_session.login.get_auth_token(),
                        streamer.username,
                    )
                return streamer

            streamers_loaded: list[None | Streamer] = [None] * len(streamers_pre_loaded)
            if streamers_pre_loaded:
                with ThreadPoolExecutor(max_workers=load_workers or 1) as executor:
                    futures = {
                        executor.submit(build_streamer, username, source): index
                        for index, (username, source) in enumerate(streamers_pre_loaded)
                    }
                    for future in as_completed(futures):
                        index = futures[future]
                        username = streamers_pre_loaded[index]
                        try:
                            streamers_loaded[index] = future.result()
                        except StreamerDoesNotExistException:
                            logger.info(
                                f"Streamer {username} does not exist",
                                extra={"emoji": ":cry:"},
                            )
                        except Exception:
                            logger.error(
                                f"Failed to load streamer {username}", exc_info=True
                            )

            self.streamers = [
                streamer for streamer in streamers_loaded if streamer is not None
            ]

            # Populate the streamers with default values.
            # 1. Load channel points and auto-claim bonus
            # 2. Check if streamers are online
            # 3. DEACTIVATED: Check if the user is a moderator. (was used before the 5th of April 2021 to deactivate predictions)
            invalid_streamers = self.twitch.initialize_streamers_context(self.streamers)
            if invalid_streamers:
                self.streamers = [
                    streamer
                    for streamer in self.streamers
                    if streamer.username not in invalid_streamers
                ]
                if not self.streamers:
                    logger.error("No valid streamers available after initialization.")
                    self.end()
                    return

            self.original_streamers = [
                streamer.channel_points for streamer in self.streamers
            ]

            # If we have at least one streamer with settings = make_predictions True
            make_predictions = at_least_one_value_in_settings_is(
                self.streamers, "make_predictions", True
            )

            background_task_sleep_step = timedelta(seconds=5).total_seconds()

            # If we have at least one streamer with settings = claim_drops True
            # Spawn a thread for sync inventory and dashboard
            if (
                at_least_one_value_in_settings_is(self.streamers, "claim_drops", True)
                is True
            ):
                sync_campaigns_thread = threading.Thread(
                    target=self.twitch.sync_campaigns,
                    args=(self.streamers,),
                )
                sync_campaigns_thread.name = "Sync campaigns/inventory"
                sync_campaigns_thread.start()
                self.background_tasks.append(sync_campaigns_thread)

            minute_watcher_thread = threading.Thread(
                target=self.twitch.send_minute_watched_events,
                args=(self.streamers, self.streamer_selector),
            )
            minute_watcher_thread.name = "Minute watcher"
            minute_watcher_thread.start()
            self.background_tasks.append(minute_watcher_thread)

            # Periodic task to update the client version
            update_client_version_period = timedelta(hours=10).total_seconds()
            update_client_version_thread = threading.Thread(
                target=lambda: interruptible_repeating_task(
                    self.twitch.update_client_version,
                    lambda: self.running,
                    lambda: self.twitch.client_session.version_outdated,
                    update_client_version_period,
                    background_task_sleep_step,
                ),
            )
            update_client_version_thread.name = "Update client version"
            update_client_version_thread.start()
            self.background_tasks.append(update_client_version_thread)

            pubsub_handlers = [PubSubHandler(self.twitch, self.streamers, self.events_predictions)]
            if Settings.use_hermes:
                self.ws_pool = HermesWebSocketPool(
                    url=f"{HERMES_WEBSOCKET}?clientId={CLIENT_ID_WEB}",
                    twitch=self.twitch,
                    request_encoder=hermes_data.JsonEncoder(),
                    response_decoder=hermes_data.JsonDecoder(),
                    listeners=pubsub_handlers,
                )
            else:
                self.ws_pool = PubSubWebSocketPool(twitch=self.twitch, listeners=pubsub_handlers)

            self.ws_pool.start()

            # Subscribe to community-points-user. Get update for points spent or gains
            user_id = self.twitch.client_session.login.get_user_id()
            # print(f"!!!!!!!!!!!!!! USER_ID: {user_id}")

            # Fixes 'ERR_BADAUTH'
            if not user_id:
                logger.error("No user_id, exiting...")
                self.end()

            self.ws_pool.submit(
                PubsubTopic(
                    "community-points-user-v1",
                    user_id=user_id,
                )
            )

            # Going to subscribe to predictions-user-v1. Get update when we place a new prediction (confirm)
            if make_predictions is True:
                self.ws_pool.submit(
                    PubsubTopic(
                        "predictions-user-v1",
                        user_id=user_id,
                    )
                )

            for streamer in self.streamers:
                self.ws_pool.submit(
                    PubsubTopic("video-playback-by-id", streamer=streamer)
                )

                if streamer.settings.follow_raid is True:
                    self.ws_pool.submit(PubsubTopic("raid", streamer=streamer))

                if streamer.settings.make_predictions is True:
                    self.ws_pool.submit(
                        PubsubTopic("predictions-channel-v1", streamer=streamer)
                    )

                if streamer.settings.claim_moments is True:
                    self.ws_pool.submit(
                        PubsubTopic("community-moments-channel-v1", streamer=streamer)
                    )

                if streamer.settings.community_goals is True:
                    self.ws_pool.submit(
                        PubsubTopic("community-points-channel-v1", streamer=streamer)
                    )

            # Periodic task to check the websockets for stale connections
            websocket_jitter_min = timedelta(seconds=20).total_seconds()
            websocket_jitter_max = timedelta(seconds=60).total_seconds()

            def websocket_task():
                while (
                    self.running
                    and self.ws_pool is not None
                    and interruptible_sleep(
                        lambda: self.running,
                        random.uniform(websocket_jitter_min, websocket_jitter_max),
                        background_task_sleep_step,
                    )
                ):
                    try:
                        self.ws_pool.check_stale_connections()
                    except Exception as e:
                        # Report the error but allow the task to continue
                        logger.error(f"Error when checking stale websocket connections: {e}")

            ws_thread = threading.Thread(target=websocket_task)
            ws_thread.name = "WebSocket check stale connections"
            ws_thread.start()
            self.background_tasks.append(ws_thread)

            # Periodic task to refresh all channel points contexts
            context_refresh_period = timedelta(minutes=30).total_seconds()
            context_refresh_thread = threading.Thread(
                target=lambda: interruptible_repeating_task(
                    lambda: self.twitch.refresh_streamer_contexts(self.streamers),
                    lambda: self.running,
                    lambda: False,
                    context_refresh_period,
                    background_task_sleep_step,
                ),
            )
            context_refresh_thread.name = "Refresh channel points contexts"
            context_refresh_thread.start()
            self.background_tasks.append(context_refresh_thread)

            # Main loop, sleeps and checks on background tasks/running state
            main_loop_period = timedelta(seconds=30).total_seconds()

            def not_is_alive(thread: threading.Thread):
                return not thread.is_alive()

            while self.running:
                interruptible_sleep(lambda: self.running, main_loop_period, 5)
                if any(map(not_is_alive, self.background_tasks)):
                    logger.error(
                        f"Background task(s) {list(map(lambda task: task.name, filter(not_is_alive, self.background_tasks)))} have stopped working. Stopping application."
                    )
                    break
        finally:
            self.end()

    def end_signal(self, signum, frame):
        if not self.running:
            return

        logger.info("CTRL+C Detected! Please wait just a moment!")
        self.end()

    def end(self):
        if not self.running:
            return

        for streamer in self.streamers:
            if streamer.irc_chat is not None and streamer.settings.chat != ChatPresence.NEVER:
                streamer.leave_chat()
                if streamer.irc_chat.is_alive() is True:
                    streamer.irc_chat.join()

        self.running = self.twitch.running = False
        if self.ws_pool is not None:
            self.ws_pool.end()

        for task in self.background_tasks:
            task.join()

        # Check if all the mutex are unlocked.
        # Prevent breaks of .json file
        for streamer in self.streamers:
            if streamer.mutex.locked():
                streamer.mutex.acquire()
                streamer.mutex.release()

        self.__print_report()

        # Stop the queue listener to make sure all messages have been logged
        self.queue_listener.stop()

        sys.exit(0)

    def __print_report(self):
        print("\n")
        logger.info(
            f"Ending session: '{self.session_id}'", extra={"emoji": ":stop_sign:"}
        )
        if self.logs_file is not None:
            logger.info(
                f"Logs file: {self.logs_file}", extra={"emoji": ":page_facing_up:"}
            )
        logger.info(
            f"Duration {datetime.now() - self.start_datetime}",
            extra={"emoji": ":hourglass:"},
        )

        if not Settings.logger.less and self.events_predictions != {}:
            print("")
            for event_id in self.events_predictions:
                event = self.events_predictions[event_id]
                if (
                        event.bet_confirmed is True
                        and event.streamer.settings.make_predictions is True
                ):
                    logger.info(
                        f"{event.streamer.settings.bet}",
                        extra={"emoji": ":wrench:"},
                    )
                    if event.streamer.settings.bet.filter_condition is not None:
                        logger.info(
                            f"{event.streamer.settings.bet.filter_condition}",
                            extra={"emoji": ":pushpin:"},
                        )
                    logger.info(
                        f"{event.print_recap()}",
                        extra={"emoji": ":bar_chart:"},
                    )

        print("")
        for streamer_index in range(0, len(self.streamers)):
            if self.streamers[streamer_index].history != {}:
                gained = self.streamers[streamer_index].channel_points - self.original_streamers[streamer_index]

                from colorama import Fore
                streamer_highlight = Fore.YELLOW

                streamer_gain = (
                    f"{streamer_highlight}{self.streamers[streamer_index]}{Fore.RESET}, Total Points Gained: {millify(gained)}"
                    if Settings.logger.less
                    else f"{streamer_highlight}{repr(self.streamers[streamer_index])}{Fore.RESET}, Total Points Gained (after farming - before farming): {millify(gained)}"
                )

                indent = ' ' * 25
                streamer_history = '\n'.join(
                    f"{indent}{history}" for history in self.streamers[streamer_index].print_history().split('; ')
                )

                logger.info(
                    f"{streamer_gain}\n{streamer_history}",
                    extra={"emoji": ":moneybag:"},
                )
