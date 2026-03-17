# For documentation on Twitch GraphQL API see:
# https://www.apollographql.com/docs/
# https://github.com/mauricew/twitch-graphql-api
# Full list of available methods: https://azr.ivr.fi/schema/query.doc.html (a bit outdated)


import logging
import os
import random
import re
import string
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed, Future
from pathlib import Path
from secrets import choice, token_hex

import requests

from TwitchChannelPointsMiner.classes.StreamerSelector import StreamerSelector
from TwitchChannelPointsMiner.classes.ClientSession import ClientSession
from TwitchChannelPointsMiner.classes.Exceptions import (
    StreamerDoesNotExistException,
    StreamerIsOfflineException,
)
from TwitchChannelPointsMiner.classes.Settings import (
    Events,
    FollowersOrder,
    Settings,
)
from TwitchChannelPointsMiner.classes.TwitchLogin import TwitchLogin
from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.CommunityGoal import CommunityGoal
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.gql.Errors import RetryError
from TwitchChannelPointsMiner.classes.gql.Integration import GQLFactory
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropCampaignInProgress,
    DropCampaignDetails,
    DropCampaignDashboard,
)
from TwitchChannelPointsMiner.constants import (
    CLIENT_ID,
    CLIENT_VERSION,
    URL,
)
from TwitchChannelPointsMiner.utils import (
    millify,
    internet_connection_available,
    interruptible_sleep,
)

logger = logging.getLogger(__name__)

STREAMER_INIT_TIMEOUT_PER_STREAMER = 5  # seconds
CLIENT_WATCH_SECONDS = 20


class Twitch(object):
    __slots__ = [
        "cookies_file",
        "running",
        "client_session",
        "gql",
        "twilight_build_id_pattern",
    ]

    def __init__(
        self,
        username,
        user_agent,
        password=None,
        gql_factory: GQLFactory | None = None,
    ):
        cookies_path = os.path.join(Path().absolute(), "cookies")
        Path(cookies_path).mkdir(parents=True, exist_ok=True)
        self.cookies_file = os.path.join(cookies_path, f"{username}.pkl")
        self.twilight_build_id_pattern = re.compile(
            r'window\.__twilightBuildID\s*=\s*"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"'
        )
        device_id = "".join(
            choice(string.ascii_letters + string.digits) for _ in range(32)
        )
        twitch_login = TwitchLogin(
            CLIENT_ID, device_id, username, user_agent, password=password
        )
        client_session_id = token_hex(16)
        self.client_session = ClientSession(
            login=twitch_login,
            user_agent=user_agent,
            version=CLIENT_VERSION,
            device_id=device_id,
            session_id=client_session_id,
            version_outdated=True,
        )
        gql_factory = gql_factory if gql_factory is not None else GQLFactory()
        self.gql = gql_factory.create(self.client_session)
        self.running = True

    def login(self):
        if not os.path.isfile(self.cookies_file):
            if self.client_session.login.login_flow():
                self.client_session.login.save_cookies(self.cookies_file)
        else:
            self.client_session.login.load_cookies(self.cookies_file)
            self.client_session.login.set_token(
                self.client_session.login.get_auth_token()
            )

    # === STREAMER / STREAM / INFO === #
    def update_stream(self, streamer: Streamer):
        if streamer.stream.update_required() is True:
            stream_info, is_live_info, watch_streak_milestone, ban_status = (
                self.get_stream_info(streamer)
            )
            if (
                stream_info is not None
                and stream_info.stream is not None
                and is_live_info is not None
                and is_live_info.stream is not None
            ):
                streamer.chat_banned = ban_status is not None
                streak_was_missing = streamer.stream.watch_streak_missing
                streamer.stream.update(
                    broadcast_id=stream_info.stream.id,
                    title=stream_info.broadcast_settings.title,
                    game=stream_info.broadcast_settings.game,
                    tags=stream_info.stream.tags,
                    viewers_count=stream_info.stream.viewers_count,
                    created_at=is_live_info.stream.created_at,
                    watch_streak_milestone=watch_streak_milestone,
                )
                if streak_was_missing and not streamer.stream.watch_streak_missing:
                    logger.info(
                        f"Detected WATCH_STREAK for {streamer}",
                        extra={
                            "emoji": ":rocket:",
                            "event": Events.get("WATCH_STREAK_PROGRESS"),
                        }
                    )

                event_properties = {
                    "channel_id": streamer.channel_id,
                    "broadcast_id": streamer.stream.broadcast_id,
                    "player": "site",
                    "user_id": self.client_session.login.get_user_id(),
                    "live": True,
                    "channel": streamer.username,
                }

                if (
                    streamer.stream.game_name() is not None
                    and streamer.stream.game_id() is not None
                    and streamer.settings.claim_drops is True
                ):
                    event_properties["game"] = streamer.stream.game_name()
                    event_properties["game_id"] = streamer.stream.game_id()
                    # Update also the campaigns_ids so we are sure to tracking the correct campaign
                    streamer.stream.campaigns_ids = (
                        self.__get_campaign_ids_from_streamer(streamer)
                    )

                streamer.stream.payload = [
                    {"event": "minute-watched", "properties": event_properties}
                ]

    def get_spade_url(self, streamer):
        try:
            # fixes AttributeError: 'NoneType' object has no attribute 'group'
            # headers = {"User-Agent": self.user_agent}
            from TwitchChannelPointsMiner.constants import USER_AGENTS

            headers = {"User-Agent": USER_AGENTS["Linux"]["FIREFOX"]}

            main_page_request = requests.get(streamer.streamer_url, headers=headers)
            response = main_page_request.text
            # logger.info(response)
            regex_settings = "(https://static.twitchcdn.net/config/settings.*?js|https://assets.twitch.tv/config/settings.*?.js)"
            settings_url = re.search(regex_settings, response).group(1)

            settings_request = requests.get(settings_url, headers=headers)
            response = settings_request.text
            regex_spade = '"spade_url":"(.*?)"'
            streamer.stream.spade_url = re.search(regex_spade, response).group(1)
        except requests.exceptions.RequestException as e:
            logger.error(f"Something went wrong during extraction of 'spade_url': {e}")

    def get_stream_info(self, streamer: Streamer):
        """
        Gets information about the stream for the given streamer.
        :param streamer: The streamer to check.
        :return: The stream info or None if a stream is not currently in progress or an error occurs.
        :raises RetryError: If we can't make the request and so don't know if they're online.
        :raises StreamerIsOfflineException: If the streamer is offline.
        """
        try:
            info_response = self.gql.video_player_stream_info_overlay_channel(
                streamer.username
            )
            is_live_response = self.gql.with_is_stream_live_query(streamer.channel_id)
            reward_list_response = self.gql.reward_list(streamer.channel_id)
            chat_room_ban_status = self.gql.chat_room_ban_status(
                self.client_session.login.get_user_id(), streamer.channel_id
            )
        except RetryError as e:
            logger.error(f"Error getting stream info for {Settings.logger.anonymiser.streamer_username(streamer)}: {e}")
            raise e
        if info_response.user.stream is None:
            # There is no stream data, so they're offline
            raise StreamerIsOfflineException
        else:
            return (
                info_response.user,
                is_live_response.user,
                reward_list_response.channel.self.watch_streak_milestone,
                chat_room_ban_status.status
            )

    def check_streamer_online(self, streamer):
        if time.time() < streamer.offline_at + 60:
            return

        if streamer.is_online is False:
            try:
                self.get_spade_url(streamer)
                self.update_stream(streamer)
            except StreamerIsOfflineException:
                streamer.set_offline()
            except RetryError:
                pass
            else:
                streamer.set_online()
        else:
            try:
                self.update_stream(streamer)
            except StreamerIsOfflineException:
                streamer.set_offline()
            except RetryError:
                pass

    def get_channel_id(self, streamer_username: str) -> str:
        """
        Gets the channel id for the streamer with the given username.
        :param streamer_username: The username of the streamer.
        :return: The channel id.
        :raises StreamerDoesNotExistException:
            If a streamer with the given username does not exist or another error occurs.
            TODO should we return/raise something else if an error occurs and we don't know if the streamer exists?
        """
        try:
            response = self.gql.get_id_from_login(streamer_username)
            if response.id == "":
                raise StreamerDoesNotExistException
            else:
                return response.id
        except RetryError as e:
            logger.error(f"Error getting channel id for {Settings.logger.anonymiser.username(streamer_username)}: {e}")
            raise StreamerDoesNotExistException

    def get_followers(
        self, limit: int = 100, order: FollowersOrder = FollowersOrder.ASC
    ):
        """
        Gets the list of channel logins for the user's followers.
        :param limit: The maximum amount of logins to get per request.
        :param order: The order in which to retrieve the logins.
        :return: The logins or an empty list if an error occurs (or there are no followers).
        """
        try:
            return self.gql.channel_follows(limit, order)
        except RetryError as e:
            logger.error(
                f"Error getting user's followers. Limit: {limit}, order: '{order}: {e}'"
            )
            return []

    def update_raid(self, streamer, raid):
        if streamer.raid != raid:
            streamer.raid = raid
            target = Settings.logger.anonymiser.username(raid.target_login)
            try:
                self.gql.join_raid(raid.raid_id)
                logger.info(
                    f"Joining raid from {streamer} to {target}!",
                    extra={"emoji": ":performing_arts:", "event": Events.JOIN_RAID},
                )
            except RetryError as e:
                logger.error(f"Error joining raid from {streamer} to {target}: {e}")

    # === 'GLOBALS' METHODS === #
    # Create chunk of sleep of speed-up the break loop after CTRL+C
    def __chuncked_sleep(self, seconds, chunk_size=3):
        step = max(seconds / max(chunk_size, 1), 0.5)
        interruptible_sleep(lambda: self.running, seconds, step=step)

    def __check_connection_handler(self, chunk_size):
        # The success rate It's very high usually. Why we have failed?
        # Check internet connection ...
        while internet_connection_available() is False:
            random_sleep = random.randint(1, 3)
            logger.warning(
                f"No internet connection available! Retry after {random_sleep}m"
            )
            self.__chuncked_sleep(random_sleep * 60, chunk_size=chunk_size)

    # Request for Integrity Token
    # Twitch needs Authorization, Client-Id, X-Device-Id to generate JWT which is used for authorize gql requests
    # Regenerate Integrity Token 5 minutes before expire
    """def post_integrity(self):
        if (
            self.integrity_expire - datetime.now().timestamp() * 1000 > 5 * 60 * 1000
            and self.integrity is not None
        ):
            return self.integrity
        try:
            response = requests.post(
                GQLOperations.integrity_url,
                json={},
                headers={
                    "Authorization": f"OAuth {self.twitch_login.get_auth_token()}",
                    "Client-Id": CLIENT_ID,
                    "Client-Session-Id": self.client_session,
                    "Client-Version": self.update_client_version(),
                    "User-Agent": self.user_agent,
                    "X-Device-Id": self.device_id,
                },
            )
            logger.debug(
                f"Data: [], Status code: {response.status_code}, Content: {response.text}"
            )
            self.integrity = response.json().get("token", None)
            # logger.info(f"integrity: {self.integrity}")

            if self.isBadBot(self.integrity) is True:
                logger.info(
                    "Uh-oh, Twitch has detected this miner as a \"Bad Bot\". Don't worry.")

            self.integrity_expire = response.json().get("expiration", 0)
            # logger.info(f"integrity_expire: {self.integrity_expire}")
            return self.integrity
        except requests.exceptions.RequestException as e:
            logger.error(f"Error with post_integrity: {e}")
            return self.integrity

    # verify the integrity token's contents for the "is_bad_bot" flag
    def isBadBot(self, integrity):
        stripped_token: str = self.integrity.split('.')[2] + "=="
        messy_json: str = urlsafe_b64decode(
            stripped_token.encode()).decode(errors="ignore")
        match = re.search(r'(.+)(?<="}).+$', messy_json)
        if match is None:
            # raise MinerException("Unable to parse the integrity token")
            logger.info("Unable to parse the integrity token. Don't worry.")
            return
        decoded_header = json.loads(match.group(1))
        # logger.info(f"decoded_header: {decoded_header}")
        if decoded_header.get("is_bad_bot", "false") != "false":
            return True
        else:
            return False"""

    def update_client_version(self) -> str:
        try:
            # Set the version as up to date to avoid spamming requests
            self.client_session.version_outdated = False
            response = requests.get(URL)
            if response.status_code != 200:
                logger.debug(
                    f"Error with update_client_version: {response.status_code}"
                )
                return self.client_session.version
            matcher = re.search(self.twilight_build_id_pattern, response.text)
            if not matcher:
                logger.debug("Error with update_client_version: no match")
                return self.client_session.version
            self.client_session.version = matcher.group(1)
            logger.debug(f"Client version: {self.client_session.version}")
            return self.client_session.version
        except requests.exceptions.RequestException as e:
            logger.error(f"Error with update_client_version: {e}")
            return self.client_session.version

    def send_minute_watched_events(
        self,
        streamers: list[Streamer],
        streamer_selector: StreamerSelector,
        chunk_size=3,
    ):

        def find_streamer(channel_id: str) -> Streamer:
            for streamer in streamers:
                if streamer.channel_id == channel_id:
                    return streamer
            raise KeyError(
                f"Streamer with channel_id ({channel_id}) not found in streamer list."
            )

        while self.running:
            try:
                online_streamers = [
                    streamer
                    for streamer in streamers
                    if streamer.is_online is True
                    and (
                        streamer.online_at == 0
                        or (time.time() - streamer.online_at) > 30
                    )
                    and streamer.channel_points_enabled
                    and not streamer.chat_banned
                ]

                for streamer in online_streamers:
                    if (streamer.stream.update_elapsed() / 60) > 10:
                        # Why this user It's currently online but the last updated was more than 10minutes ago?
                        # Please perform a manually update and check if the user it's online
                        self.check_streamer_online(streamer)

                selected_streamer_ids = streamer_selector.select(online_streamers, 2)
                streamers_watching = [find_streamer(streamer_id) for streamer_id in selected_streamer_ids]

                watch_attempts_start_time = time.time()

                for streamer in streamers_watching:
                    next_iteration = time.time() + CLIENT_WATCH_SECONDS / len(
                        streamers_watching
                    )

                    try:
                        response = requests.post(
                            streamer.stream.spade_url,  # pyright: ignore [reportArgumentType]
                            data=streamer.stream.encode_payload(),
                            headers={"User-Agent": self.client_session.user_agent},
                            timeout=CLIENT_WATCH_SECONDS,
                        )
                        logger.debug(
                            f"Send minute watched request for {streamer} - Status code: {response.status_code}"
                        )
                        if response.status_code == 204:
                            streamer.stream.update_minute_watched()

                            """
                            Remember, you can only earn progress towards a time-based Drop on one participating channel at a time.  [ ! ! ! ]
                            You can also check your progress towards Drops within a campaign anytime by viewing the Drops Inventory.
                            For time-based Drops, if you are unable to claim the Drop in time, you will be able to claim it from the inventory page until the Drops campaign ends.
                            """

                            for campaign in streamer.stream.campaigns:
                                for drop in campaign.drops:
                                    # We could add .has_preconditions_met condition inside is_printable
                                    if (
                                        drop.has_preconditions_met is not False
                                        and drop.is_printable is True
                                    ):
                                        drop_messages = [
                                            f"{streamer} is streaming {streamer.stream}",
                                            f"Campaign: {campaign}",
                                            f"Drop: {drop}",
                                            f"{drop.progress_bar()}",
                                        ]
                                        for single_line in drop_messages:
                                            logger.info(
                                                single_line,
                                                extra={
                                                    "event": Events.DROP_STATUS,
                                                    "skip_telegram": True,
                                                    "skip_discord": True,
                                                    "skip_webhook": True,
                                                    "skip_matrix": True,
                                                    "skip_gotify": True,
                                                    "skip_pushover": True
                                                },
                                            )

                                        if len(Settings.logger.hooks) > 0:
                                            combined_message = "\n".join(drop_messages)
                                            for hook in Settings.logger.hooks:
                                                hook.send(combined_message, Events.DROP_STATUS)

                    except requests.exceptions.ConnectionError as e:
                        logger.error(f"Error while trying to send minute watched: {e}")
                        self.__check_connection_handler(chunk_size)
                    except requests.exceptions.Timeout as e:
                        logger.error(f"Error while trying to send minute watched: {e}")

                    self.__chuncked_sleep(
                        next_iteration - time.time(), chunk_size=chunk_size
                    )

                # Ensure we sleep at least 20 seconds, even if we `continue` iteration(s)
                time_remaining = CLIENT_WATCH_SECONDS - (time.time() - watch_attempts_start_time)
                if len(streamers_watching) == 0 or time_remaining > 0.01:
                    self.__chuncked_sleep(time_remaining, chunk_size=chunk_size)
            except Exception:
                logger.error(
                    "Exception raised in send minute watched", exc_info=True)
                # Do a short sleep to avoid error log spam
                time.sleep(1)

    # === CHANNEL POINTS / PREDICTION === #
    # Load the amount of current points for a channel, check if a bonus is available
    def load_channel_points_context(self, streamer: Streamer):
        try:
            response = self.gql.get_channel_points_context(streamer.username)
        except RetryError as e:
            logger.error(f"Error while trying to load channel points context: {e}")
            return
        if response.community is None:
            raise StreamerDoesNotExistException
        channel = response.community.channel
        community_points = channel.edge.community_points
        streamer.channel_points_enabled = channel.community_points_settings.is_enabled
        streamer.channel_points = community_points.balance
        streamer.active_multipliers = community_points.active_multipliers

        if streamer.settings.community_goals is True:
            streamer.community_goals = {
                goal.id: CommunityGoal.from_gql(goal)
                for goal in channel.community_points_settings.goals
            }

        if community_points.available_claim is not None:
            self.claim_bonus(streamer, community_points.available_claim.id)

        if streamer.settings.community_goals is True:
            self.contribute_to_community_goals(streamer)

    def initialize_streamers_context(self, streamers: list[Streamer], max_workers=10) -> set[str]:
        """
        Initializes the context for the given Streamers. Loads the channel points context and checks if they're online.
        Parallelizes execution across the given number of worker threads.
        :param streamers: The Streamers to initialize.
        :param max_workers: The maximum number of worker threads.
        :return: The usernames of any Streamers that failed to initialize.
        """
        if not streamers:
            return set()

        failed_streamers: set[str] = set()

        def _load_streamer_context(streamer):
            time.sleep(random.uniform(0.15, 0.35))
            self.load_channel_points_context(streamer)
            self.check_streamer_online(streamer)

        # Initialize channel context in parallel so large streamer lists do not block startup
        workers = max(1, min(max_workers, len(streamers)))
        timeout_seconds = STREAMER_INIT_TIMEOUT_PER_STREAMER * len(streamers)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures: dict[Future[None], Streamer] = {
                executor.submit(_load_streamer_context, streamer): streamer
                for streamer in streamers
            }
            try:
                for future in as_completed(futures, timeout=timeout_seconds):
                    streamer = futures[future]
                    try:
                        future.result()
                    except StreamerDoesNotExistException:
                        failed_streamers.add(streamer.username)
                        logger.info(
                            f"Streamer {Settings.logger.anonymiser.streamer_username(streamer)} does not exist",
                            extra={"emoji": ":cry:"},
                        )
                    except Exception:
                        failed_streamers.add(streamer.username)
                        logger.error(
                            f"Failed to initialize streamer {Settings.logger.anonymiser.streamer_username(streamer)}",
                            exc_info=True,
                        )
            except TimeoutError:
                logger.error(
                    "Timed out while initializing streamers after %s seconds.",
                    timeout_seconds,
                )
                for future, streamer in futures.items():
                    if not future.done():
                        failed_streamers.add(streamer.username)
        return failed_streamers

    def refresh_streamer_contexts(self, streamers: list[Streamer]):
        """
        Refreshes the channel points contexts for the given Streamers.
        :param streamers: The streamers to refresh.
        """
        for streamer in streamers:
            if streamer.is_online:
                try:
                    self.load_channel_points_context(streamer)
                except StreamerDoesNotExistException:
                    logger.warning(
                        f"Detected that Streamer '{Settings.logger.anonymiser.streamer_username(streamer)}' no longer exists."
                    )
                    pass

    def make_predictions(self, event):
        decision = event.bet.calculate(event.streamer.channel_points)
        # selector_index = 0 if decision["choice"] == "A" else 1

        logger.info(
            f"Going to complete bet for {event}",
            extra={
                "emoji": ":four_leaf_clover:",
                "event": Events.BET_GENERAL,
            },
        )
        if event.status == "ACTIVE":
            skip, compared_value = event.bet.skip()
            if skip is True:
                logger.info(
                    f"Skip betting for the event {event}",
                    extra={
                        "emoji": ":pushpin:",
                        "event": Events.BET_FILTERS,
                    },
                )
                logger.info(
                    f"Skip settings {event.bet.settings.filter_condition}, current value is: {compared_value}",
                    extra={
                        "emoji": ":pushpin:",
                        "event": Events.BET_FILTERS,
                    },
                )
            else:
                if decision["amount"] >= 10:
                    logger.info(
                        # f"Place {millify(decision['amount'])} channel points on: {event.bet.get_outcome(selector_index)}",
                        f"Place {millify(decision['amount'])} channel points on: {event.bet.get_outcome(decision['choice'])}",
                        extra={
                            "emoji": ":four_leaf_clover:",
                            "event": Events.BET_GENERAL,
                        },
                    )

                    try:
                        response = self.gql.make_prediction(
                            event.event_id, decision["id"], decision["amount"]
                        )
                    except RetryError as e:
                        logger.error(f"Error while trying to make prediction: {e}")
                        return

                    if response.error is not None:
                        error_code = response.error.code
                        logger.error(
                            f"Failed to place bet, error: {error_code}",
                            extra={
                                "emoji": ":four_leaf_clover:",
                                "event": Events.BET_FAILED,
                            },
                        )
                else:
                    logger.info(
                        f"Bet won't be placed as the amount {millify(decision['amount'])} is less than the minimum required 10",
                        extra={
                            "emoji": ":four_leaf_clover:",
                            "event": Events.BET_GENERAL,
                        },
                    )
        else:
            logger.info(
                f"Oh no! The event is not active anymore! Current status: {event.status}",
                extra={
                    "emoji": ":disappointed_relieved:",
                    "event": Events.BET_FAILED,
                },
            )

    def claim_bonus(self, streamer: Streamer, claim_id: str):
        if Settings.logger.less is False:
            logger.info(
                f"Claiming the bonus for {streamer}!",
                extra={"emoji": ":gift:", "event": Events.BONUS_CLAIM},
            )
        try:
            self.gql.claim_community_points(streamer.channel_id, claim_id)
        except RetryError as e:
            logger.error(
                f"Error while trying to claim bonus for {Settings.logger.anonymiser.streamer_username(streamer)}: {e}"
            )

    # === MOMENTS === #
    def claim_moment(self, streamer: Streamer, moment_id: str):
        if Settings.logger.less is False:
            logger.info(
                f"Claiming the moment for {streamer}!",
                extra={"emoji": ":video_camera:", "event": Events.MOMENT_CLAIM},
            )

        try:
            self.gql.claim_moment(moment_id)
        except RetryError as e:
            logger.error(
                f"Error while trying to claim moment with id {moment_id} for {Settings.logger.anonymiser.streamer_username(streamer)}: {e}",
            )

    # === CAMPAIGNS / DROPS / INVENTORY === #
    def __get_campaign_ids_from_streamer(self, streamer):
        try:
            return self.gql.get_available_drops(streamer.channel_id).ids
        except RetryError as e:
            logger.error(
                f"Error while trying to get drops campaign ids for {Settings.logger.anonymiser.streamer_username(streamer)}: {e}"
            )
            return []

    def __get_inventory(self):
        try:
            return self.gql.get_inventory()
        except RetryError as e:
            logger.error(f"Error while trying to get user inventory: {e}")
            return None

    def __get_drops_dashboard(
        self, status: str | None = None
    ) -> list[DropCampaignDashboard]:
        try:
            campaigns = self.gql.get_viewer_drops_dashboard().campaigns or []
            if status is not None:
                status = status.upper()
                campaigns = [
                    campaign for campaign in campaigns if campaign.status == status
                ]
            return campaigns
        except RetryError as e:
            logger.error(f"Error while trying to get viewer drops dashboard: {e}")
            return []

    def __get_campaigns_details(
        self, campaigns: list[DropCampaignDashboard]
    ) -> list[DropCampaignDetails]:
        campaign_ids: list[str] = [c.id for c in campaigns]
        try:
            return [
                response.campaign
                for response in self.gql.get_drop_campaign_details(campaign_ids)
            ]
        except RetryError as e:
            logger.error(
                f"Error while trying to get campaigns details for campaigns: {campaign_ids}: {e}"
            )
            return []

    def __sync_campaigns(self, campaigns: list[Campaign]) -> list[Campaign]:
        # We need the inventory only for get the real updated value/progress
        # Get data from inventory and sync current status with streamers.campaigns
        inventory = self.__get_inventory()
        if inventory is not None and inventory.campaigns is not None:
            # Iterate all campaigns from dashboard (only active, with working drops)
            # In this array we have also the campaigns never started from us (not in nventory)
            for i in range(len(campaigns)):
                campaigns[i].clear_drops()  # Remove all the claimed drops
                # Iterate all campaigns currently in progress from out inventory
                progress: DropCampaignInProgress  # Annoyingly the IDE thinks progress is Campaign not DropCampaign
                for progress in inventory.campaigns:
                    if progress.id == campaigns[i].id:
                        campaigns[i].in_inventory = True
                        campaigns[i].sync_drops(
                            progress.time_based_drops, self.claim_drop
                        )
                        # Remove all the claimed drops
                        campaigns[i].clear_drops()
                        break
        return campaigns

    def claim_drop(self, drop: Drop):
        if drop.drop_instance_id is None:
            logger.debug(f"Unable to claim drop '{drop.id}', no instance id'")
            return False
        logger.info(
            f"Claim {drop}", extra={"emoji": ":package:", "event": Events.DROP_CLAIM}
        )
        try:
            response = self.gql.claim_drop_rewards(drop.drop_instance_id)
        except RetryError as e:
            logger.error(
                f"Error while trying to claim drop with id '{drop.drop_instance_id}': {e}"
            )
            return False
        if response.status is None:
            return False
        if response.errors is not None and len(response.errors) > 0:
            logger.error(
                f"Errors while trying to claim drop with id '{drop.drop_instance_id}': {response.errors}"
            )
            return False
        if response.status in ["ELIGIBLE_FOR_ALL", "DROP_INSTANCE_ALREADY_CLAIMED"]:
            return True
        return False

    def claim_all_drops_from_inventory(self):
        inventory = self.__get_inventory()
        if inventory is not None:
            if inventory.campaigns is not None:
                for campaign in inventory.campaigns:
                    for time_based_drop in campaign.time_based_drops:
                        drop = Drop(time_based_drop)
                        drop.update(time_based_drop.self_edge)
                        if drop.is_claimable:
                            drop.is_claimed = self.claim_drop(drop)
                            time.sleep(random.uniform(5, 10))

    def sync_campaigns(self, streamers, chunk_size=3):
        campaigns_update = 0
        campaigns = []
        while self.running:
            try:
                # Get update from dashboard each 60minutes
                if (
                    campaigns_update == 0
                    # or ((time.time() - campaigns_update) / 60) > 60
                    # TEMPORARY AUTO DROP CLAIMING FIX
                    # 30 minutes instead of 60 minutes
                    or ((time.time() - campaigns_update) / 30) > 30
                    #####################################
                ):
                    campaigns_update = time.time()

                    # TEMPORARY AUTO DROP CLAIMING FIX
                    self.claim_all_drops_from_inventory()
                    #####################################

                    # Get full details from current ACTIVE campaigns
                    # Use dashboard so we can explore new drops not currently active in our Inventory
                    campaigns_details = self.__get_campaigns_details(
                        self.__get_drops_dashboard(status="ACTIVE")
                    )
                    campaigns = []

                    # Going to clear array and structure. Remove all the timeBasedDrops expired or not started yet
                    for index in range(0, len(campaigns_details)):
                        if campaigns_details[index] is not None:
                            campaign = Campaign(campaigns_details[index])
                            if campaign.dt_match is True:
                                # Remove all the drops already claimed or with dt not matching
                                campaign.clear_drops()
                                if campaign.drops != []:
                                    campaigns.append(campaign)
                        else:
                            continue

                # Divide et impera :)
                campaigns = self.__sync_campaigns(campaigns)

                # Check if user It's currently streaming the same game present in campaigns_details
                for i in range(0, len(streamers)):
                    if streamers[i].should_sync_campaigns() is True:
                        # yes! The streamer[i] have the drops_tags enabled and we It's currently stream a game with campaign active!
                        # With 'campaigns_ids' we are also sure that this streamer have the campaign active.
                        # yes! The streamer[index] have the drops_tags enabled and we It's currently stream a game with campaign active!
                        streamers[i].stream.campaigns = list(
                            filter(
                                lambda x: x.drops != []
                                and x.game == streamers[i].stream.game
                                and x.id in streamers[i].stream.campaigns_ids,
                                campaigns,
                            )
                        )

            except (
                ValueError,
                KeyError,
                requests.exceptions.ConnectionError,
                RetryError,
            ) as e:
                logger.error(f"Error while syncing inventory: {e}")
                campaigns = []
                self.__check_connection_handler(chunk_size)

            self.__chuncked_sleep(60, chunk_size=chunk_size)

    def contribute_to_community_goals(self, streamer: Streamer):
        # Don't bother doing the request if no goal is currently started or in stock
        if any(
            goal.status == "STARTED" and goal.is_in_stock
            for goal in streamer.community_goals.values()
        ):
            try:
                response = self.gql.get_user_points_contribution(streamer.username)
            except RetryError as e:
                logger.error(f"Error while trying to get user points contribution: {e}")
                return
            user_goal_contributions = response.goal_contributions
            logger.debug(
                f"Found {len(user_goal_contributions)} community goals for {Settings.logger.anonymiser.streamer_username(streamer)}'s current stream"
            )
            for goal_contribution in user_goal_contributions:
                goal_id = goal_contribution.id
                goal = streamer.community_goals[goal_id]
                if goal is None:
                    # TODO should this trigger a new load context request
                    logger.error(
                        f"Unable to find context data for {Settings.logger.anonymiser.streamer_username(streamer)}'s community goal {goal_id}"
                    )
                else:
                    user_stream_contribution = (
                        goal_contribution.user_points_contributed_this_stream
                    )
                    user_left_to_contribute = (
                        goal.per_stream_user_maximum_contribution
                        - user_stream_contribution
                    )
                    amount = min(
                        goal.amount_left(),
                        user_left_to_contribute,
                        streamer.channel_points,
                    )
                    if amount > 0:
                        self.contribute_to_community_goal(
                            streamer, goal_id, goal.title, amount
                        )
                    else:
                        logger.debug(
                            f"Not contributing to community goal {goal.title}, user channel points {streamer.channel_points}, user stream contribution {user_stream_contribution}, all users total contribution {goal.points_contributed}"
                        )

    def contribute_to_community_goal(
        self, streamer: Streamer, goal_id: str, title: str, amount: int
    ):
        try:
            response = self.gql.contribute_to_community_goal(
                streamer.channel_id, goal_id, amount
            )
        except RetryError as e:
            logger.error(
                f"Error while contributing to channel {Settings.logger.anonymiser.streamer_username(streamer)}'s community goal '{title}', amount {amount}: {e}",
            )
            return
        if response.error is not None:
            logger.error(
                f"Unable to contribute channel points to {Settings.logger.anonymiser.streamer_username(streamer)}'s community goal '{title}', reason '{response.error}'"
            )
        else:
            logger.info(
                f"Contributed {amount} channel points to community goal '{title}'"
            )
            streamer.channel_points -= amount
