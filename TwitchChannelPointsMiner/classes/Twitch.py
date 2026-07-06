# For documentation on Twitch GraphQL API see:
# https://www.apollographql.com/docs/
# https://github.com/mauricew/twitch-graphql-api
# Full list of available methods: https://azr.ivr.fi/schema/query.doc.html (a bit outdated)
import datetime
import json
import logging
import os
import random
import re
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from pathlib import Path
from secrets import choice, token_hex

import requests
import validators

from TwitchChannelPointsMiner.JsonParser import (
    JsonParentContext, expect_dict, expect_str, parse_expected_value,
    expect_list
)
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
from TwitchChannelPointsMiner.classes.StreamerSelector import StreamerSelector
from TwitchChannelPointsMiner.classes.TwitchLogin import TwitchLogin
from TwitchChannelPointsMiner.classes.entities.Campaign import Campaign
from TwitchChannelPointsMiner.classes.entities.CommunityGoal import CommunityGoal
from TwitchChannelPointsMiner.classes.entities.Drop import Drop
from TwitchChannelPointsMiner.classes.entities.GiftSub import GiftSub
from TwitchChannelPointsMiner.classes.entities.PlaybackAccessToken import (
    PlaybackAccessToken,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.Video import Video
from TwitchChannelPointsMiner.classes.gql.Errors import RetryError
from TwitchChannelPointsMiner.classes.gql.Integration import GQLFactory
from TwitchChannelPointsMiner.classes.gql.data.response.ClipsCardsUser import Clip
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropCampaignInProgress,
    DropCampaignDetails,
    DropCampaignDashboard,
)
from TwitchChannelPointsMiner.classes.gql.data.response.FilterableVideoTower import VideoEdge
from TwitchChannelPointsMiner.classes.websocket.data import WeeklyRewards
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
from TwitchChannelPointsMiner.utils.Utils import create_random_alphanumeric_id, encode_payload

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
            (
                stream_info,
                is_live_info,
                watch_streak_milestone,
                ban_status,
            ) = self.get_stream_info(streamer)
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
                        },
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
                ):
                    event_properties["game"] = streamer.stream.game_name()
                    event_properties["game_id"] = streamer.stream.game_id()

                if streamer.settings.claim_drops is True:
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

    def get_vod_playback_access_token(self, streamer: Streamer, vod_id: str):
        try:
            token = self.gql.get_video_playback_access_token(
                streamer.username, vod_id=vod_id
            )
            logger.debug(f"Obtained VOD PlaybackAccessToken for {streamer.username}")
            return token
        except RetryError as e:
            logger.error(
                f"Unable to get VOD PlaybackAccessToken for {streamer.username}: {e}"
            )
            return None

    def vod_viewable(self, streamer: Streamer, video: Video):
        """
        Returns whether a VOD is viewable, vods are not viewable if a playlist request returns HTTP statuses other than
        200.
        :param streamer: The Streamer for the VOD.
        :param video: The VOD to check.
        :return: True if the VOD is viewable, False otherwise.
        """
        if video.viewable:
            # We already know it's viewable
            return True
        if video.token is not None:
            # We've got a token and it's not viewable
            return False
        vod_id = video.edge.id
        token = self.get_vod_playback_access_token(streamer, vod_id)
        if token is None:
            return False
        video.token = token

        playlist_url = f"https://usher.ttvnw.net/vod/v2/{vod_id}.m3u8?sig={token.signature}&token={token.value}"
        logger.debug(f"Sending VOD playlist request for {vod_id} for {streamer}")
        playlist_response = requests.get(
            playlist_url,
            headers={"User-Agent": self.client_session.user_agent},
            timeout=CLIENT_WATCH_SECONDS,
        )
        logger.debug(
            f"Sent VOD playlist request for {vod_id} for {streamer}, Status: {playlist_response.status_code}"
        )
        if playlist_response.status_code == 200:
            return True
        error = None
        try:
            response_text = playlist_response.text
            response_json = expect_list(json.loads(response_text))
            if len(response_json) > 0:
                response_object = expect_dict(response_json[0])
                with JsonParentContext(0):
                    _type = parse_expected_value(response_object, "type", expect_str)
                    if _type == "error":
                        error = parse_expected_value(response_object, "error", expect_str)
        except json.JSONDecodeError:
            pass
        logger.debug(
            f"Unable to get playlist for VOD {vod_id}: status={playlist_response.status_code}{(f', error=\"{error}\"' if error is not None else '')}"
        )
        return False

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
            logger.error(
                f"Error getting stream info for {Settings.logger.anonymiser.streamer_username(streamer)}: {e}"
            )
            raise e
        if info_response.user.stream is None:
            # There is no stream data, so they're offline
            raise StreamerIsOfflineException
        else:
            return (
                info_response.user,
                is_live_response.user,
                reward_list_response.channel.self.watch_streak_milestone,
                chat_room_ban_status.status,
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
            logger.error(
                f"Error getting channel id for {Settings.logger.anonymiser.username(streamer_username)}: {e}"
            )
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

    def get_or_update_playback_access_token(
        self, streamer: Streamer, force_refresh_token: bool
    ) -> PlaybackAccessToken | None:
        """
        Gets a PlaybackAccessToken for the current Stream for the given Streamer. This may involve making a GQL
        request for a new token if one doesn't exist or the current one has expired.

        :param streamer: The Streamer for which to get the token.
        :param force_refresh_token: If True, the playback token will be refreshed.
        :return: The token or None if one could not be obtained.
        """
        if force_refresh_token or (
            streamer.settings.simulate_hls_playback is not False
            and (
                streamer.stream.playback_access_token is None
                or (
                    streamer.stream.playback_access_token.value.expires
                    - datetime.datetime.now(datetime.UTC)
                ).total_seconds()
                <= streamer.settings.simulate_hls_playback.refresh_before
            )
        ):
            try:
                gql_token = self.gql.get_playback_access_token(streamer.username)
                token = PlaybackAccessToken.from_gql(gql_token)
                streamer.stream.playback_access_token = token
                streamer.stream.hls_url = None
                logger.debug(
                    f"Obtained PlaybackAccessToken for {streamer.username}, expires {token.value.expires}"
                )
            except RetryError as e:
                logger.error(
                    f"Unable to get PlaybackAccessToken for {streamer.username}: {e}"
                )
                return None
        return streamer.stream.playback_access_token

    def get_hls_playlist_url(
        self, streamer: Streamer, force_refresh_token: bool
    ) -> str | None:
        """
        Gets the playlist URL for the current Stream for the given Streamer.

        :param streamer: The Streamer for which to get the URL.
        :param force_refresh_token: If True, the playback token will be refreshed.
        :return: The URL or None if one could not be obtained.
        """

        token = self.get_or_update_playback_access_token(streamer, force_refresh_token)
        if token is None:
            return None

        if streamer.stream.hls_url is not None:
            return streamer.stream.hls_url

        # Construct the URL for the broadcast qualities
        master_playlist_url = f"https://usher.ttvnw.net/api/channel/hls/{streamer.username}.m3u8?sig={token.signature}&token={token.raw_value}"

        # Get list of video qualities from master playlist
        logger.debug(f"Sending master playlist request for {streamer}")
        master_playlist_response = requests.get(
            master_playlist_url,
            headers={"User-Agent": self.client_session.user_agent},
            timeout=CLIENT_WATCH_SECONDS,
        )
        logger.debug(
            f"Sent master playlist request for {streamer}, Status: {master_playlist_response.status_code}"
        )

        if master_playlist_response.status_code != 200:
            logger.debug(
                f"Unable to request master playlist for {streamer}, Status: {master_playlist_response.status_code}"
            )
            return None

        broadcast_qualities_urls = master_playlist_response.text

        # Just take the last line, which should be the latest URL for the lowest quality
        lowest_quality_playlist_url = broadcast_qualities_urls.split("\n")[-1]
        if not validators.url(lowest_quality_playlist_url):
            logger.debug(
                f"Unable to parse URL from master playlist response, URL: {lowest_quality_playlist_url}"
            )
            return None
        streamer.stream.hls_url = lowest_quality_playlist_url
        return lowest_quality_playlist_url

    def simulate_hls_playback(
        self, streamer: Streamer, force_refresh_token: bool
    ) -> bool:
        """
        Simulates the HLS playback for the current Stream for the given Streamer by making a HEAD request to the latest
        stream segment.

        :param streamer: The Streamer for which to simulate playback.
        :param force_refresh_token: If True, the playback token will be refreshed.
        :return: True if playback succeeded, False otherwise.
        """
        # Twitch serves Streams via HLS which is based on M3U8 playlists. To "play back" a part of a stream you can:
        # 1. Make a request to the "usher" URL which returns the Master Playlist
        # 2. Take the last URL from the Master Playlist which should be the Lowest Quality Stream Playlist
        # 3. Make a request to the Lowest Quality Stream Playlist URL which returns the Segment Playlist
        # 4. Take the last URL from the Segment Playlist which should be the URL of the lastest Stream Segment
        # 5. Make a HEAD request to the Stream Segment URL
        # Steps 1 and 2 should only need to be done once per Stream. The rest must be done once per play back attempt
        # because the contents of the Lowest Quality Stream Playlist changes at least every 2 seconds.

        # Get the segment playlist URL for the lowest quality stream option
        stream_playlist_url = self.get_hls_playlist_url(streamer, force_refresh_token)
        if stream_playlist_url is None:
            return False

        # Get list of segment URLs
        logger.debug(f"Sending stream playlist request for {streamer}")
        stream_playlist_response = requests.get(
            stream_playlist_url,
            headers={"User-Agent": self.client_session.user_agent},
            timeout=CLIENT_WATCH_SECONDS,
        )
        logger.debug(
            f"Sent stream playlist request for {streamer}, Status: {stream_playlist_response.status_code}"
        )

        if stream_playlist_response.status_code != 200:
            logger.debug(
                f"Unable to get stream playlist, Status: {stream_playlist_response.status_code}"
            )
            return False
        stream_playlist_text = stream_playlist_response.text

        # Just take the last line, which should be the URL for the latest segment
        stream_segment_url = stream_playlist_text.split("\n")[-2]
        if not validators.url(stream_segment_url):
            logger.debug(
                f"Unable to parse latest segment URL from stream playlist, URL: {stream_segment_url}"
            )
            return False

        # Perform a HEAD request to simulate watching the stream segment
        logger.debug(f"Sending stream segment request for {streamer}")
        stream_segment_response = requests.head(
            stream_segment_url,
            headers={"User-Agent": self.client_session.user_agent},
            timeout=CLIENT_WATCH_SECONDS,
        )
        logger.debug(
            f"Sent stream segment request for {streamer}, Status: {stream_segment_response.status_code}"
        )
        return stream_segment_response.status_code == 200

    def send_spade_payload(self, streamer: Streamer, payload: list, name: str):
        """
        Sends an arbitrary spade payload to the tracking endpoint for the current Stream for the given Streamer.

        :param streamer: The Streamer for which to send the event.
        :param payload: The payload to send.
        :param name: The name of this payload, for debugging purposes.
        :return: True if the request was successful, False otherwise.
        """
        try:
            logger.debug(f"Sending spade {name} payload for {streamer}")
            response = requests.post(
                streamer.stream.spade_url,
                data=encode_payload(payload),
                headers={"User-Agent": self.client_session.user_agent},
                timeout=CLIENT_WATCH_SECONDS,
            )
            logger.debug(
                f"Sent spade {name} payload for {streamer} - {response.status_code}"
            )
            return response.status_code == 204
        except requests.exceptions.RequestException as e:
            logger.debug(f"Unable to send spade {name} for {streamer}: {e}")
            return False

    def send_spade_minute_watched_event(self, streamer: Streamer) -> bool:
        """
        Sends a minute watched event to the tracking endpoint for the current Stream for the given Streamer.

        :param streamer: The Streamer for which to send the event.
        :return: True if the request was successful, False otherwise.
        """
        return self.send_spade_payload(
            streamer, streamer.stream.payload, "minute watched"
        )

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

        watched_previous_iteration = set()
        watched_this_iteration = set()

        while self.running:
            try:
                online_streamers = [
                    streamer
                    for streamer in streamers
                    if streamer.is_online is True
                    and streamer.channel_points_enabled
                    and not streamer.chat_banned
                ]

                for streamer in online_streamers:
                    if (streamer.stream.update_elapsed() / 60) > 10:
                        # Why this user It's currently online but the last updated was more than 10minutes ago?
                        # Please perform a manually update and check if the user it's online
                        self.check_streamer_online(streamer)

                selected_streamer_ids = streamer_selector.select(online_streamers, 2)
                streamers_watching = [
                    find_streamer(streamer_id) for streamer_id in selected_streamer_ids
                ]

                # Log the difference, if any
                selected_set = set(selected_streamer_ids)
                if watched_previous_iteration != selected_set:
                    dropping = list(
                        str(find_streamer(channel_id))
                        for channel_id in watched_previous_iteration - selected_set
                    )
                    adding = list(
                        str(find_streamer(channel_id))
                        for channel_id in selected_set - watched_previous_iteration
                    )
                    logger.debug(
                        f"Changing watch slots: Adding {adding}, Dropping {dropping}"
                    )

                # Update the watch session state before starting the watch loop
                for streamer in streamers_watching:
                    if streamer.stream.watch_session_state is None:
                        # We've started a new session
                        streamer.stream.watch_session_state = datetime.datetime.now(
                            datetime.timezone.utc
                        )

                watch_attempts_start_time = time.time()

                for streamer in streamers_watching:
                    next_iteration = time.time() + CLIENT_WATCH_SECONDS / len(
                        streamers_watching
                    )

                    try:
                        if (
                            streamer.settings.simulate_hls_playback
                            and not self.simulate_hls_playback(
                                streamer,
                                streamer.channel_id not in watched_previous_iteration,
                            )
                        ):
                            continue

                        if self.send_spade_minute_watched_event(streamer):
                            watched_this_iteration.add(streamer.channel_id)
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
                                                    "skip_pushover": True,
                                                },
                                            )

                                        if len(Settings.logger.hooks) > 0:
                                            combined_message = "\n".join(drop_messages)
                                            for hook in Settings.logger.hooks:
                                                hook.send(
                                                    combined_message, Events.DROP_STATUS
                                                )

                    except requests.exceptions.ConnectionError as e:
                        logger.error(f"Error while trying to send minute watched: {e}")
                        self.__check_connection_handler(chunk_size)
                    except requests.exceptions.Timeout as e:
                        logger.error(f"Error while trying to send minute watched: {e}")

                    self.__chuncked_sleep(
                        next_iteration - time.time(), chunk_size=chunk_size
                    )

                # Ensure we sleep at least 20 seconds, even if we `continue` iteration(s)
                time_remaining = CLIENT_WATCH_SECONDS - (
                    time.time() - watch_attempts_start_time
                )
                if len(streamers_watching) == 0 or time_remaining > 0.01:
                    self.__chuncked_sleep(time_remaining, chunk_size=chunk_size)
            except Exception:
                logger.error("Exception raised in send minute watched", exc_info=True)
                # Do a short sleep to avoid error log spam
                time.sleep(1)
            watched_previous_iteration = watched_this_iteration
            watched_this_iteration = set()

    def send_clip_video_play(
        self, streamer: Streamer, clip: Clip, play_session_id: str
    ):
        """
        Sends a spade `video-play` event to the given Streamer's spade URL for the given clip.
        These events signify that the user has started playing a clip.
        :param streamer: The Streamer for the clip.
        :param clip: The clip for the event.
        :param play_session_id: The session id of the simulated player session.
        :return: True if the request was successful, False otherwise.
        """
        return self.send_spade_payload(
            streamer,
            payload=[
                {
                    "event": "video-play",
                    "properties": {
                        "location": "vod",
                        "url": clip.url,
                        "channel_id": streamer.channel_id,
                        "vod_type": "clip",
                        "vod_id": clip.id,
                        "content_mode": "clip",
                        "live": False,
                        "minutes_logged": 0,
                        "play_session_id": play_session_id,
                        "player": "site",
                        "user_id": self.client_session.login.get_user_id(),
                        "vod_timestamp": 0,
                        "clip_slug": clip.slug,
                    },
                }
            ],
            name="video play",
        )

    def send_clip_second_watched(
        self, streamer: Streamer, clip: Clip, play_session_id: str, seconds_watched: int
    ):
        """
        Sends a spade `n_second_play` event to the given Streamer's spade URL for the given clip.
        These events signify that the user has played a given number of seconds of a clip.
        :param streamer: The Streamer for the clip.
        :param clip: The clip for the event.
        :param play_session_id: The session id of the simulated player session.
        :param seconds_watched: The number of seconds the user has watched in this session.
        :return: True if the request was successful, False otherwise.
        """
        return self.send_spade_payload(
            streamer,
            payload=[
                {
                    "event": "n_second_play",
                    "properties": {
                        "location": "vod",
                        "platform": "web",
                        "url": clip.url,
                        "channel_id": streamer.channel_id,
                        "vod_type": "clip",
                        "vod_id": clip.id,
                        "live": False,
                        "minutes_logged": 0,
                        "play_session_id": play_session_id,
                        "player": "site",
                        "seconds_after_play": seconds_watched,
                        "vod_timestamp": seconds_watched - 0.1,
                        "clip_slug": clip.slug,
                        "user_id": self.client_session.login.get_user_id(),
                    },
                }
            ],
            name="second watched",
        )

    def simulate_clip_playback(
        self, streamer: Streamer, clip: Clip, max_watch_seconds: float = 20
    ):
        """
        Simulates the user watching a clip.
        :param streamer: The Streamer for whom to watch a clip.
        :param clip: The Clip to watch.
        :param max_watch_seconds: The maximum number of seconds to wait for the clip to be processed as watched.
        :return: True if playback was successful, False otherwise.
        """
        logger.info(
            f"Simulating Clip playback for {streamer} for up to {max_watch_seconds} seconds",
            extra={"emoji": ":paperclip:"},
        )
        logger.debug(f"Attempting to watch Clip '{clip.title}'")

        # Ensure we have the spade url
        if streamer.stream.spade_url is None:
            self.get_spade_url(streamer)
        if streamer.stream.spade_url is None:
            logger.debug(f"Unable to get Spade URL for {streamer}")
            return False

        # Watch the clip in 5s chunks
        max_watch_seconds = min(max_watch_seconds, clip.duration_seconds)
        start_time = time.monotonic()
        play_session_id = create_random_alphanumeric_id(32)
        self.send_clip_video_play(streamer, clip, play_session_id)
        seconds_watched = 5
        while (
            self.running
            and streamer.missing_weekly_reward()
            and time.monotonic() - start_time < max_watch_seconds
        ):
            interruptible_sleep(
                lambda: self.running and streamer.missing_weekly_reward(),
                duration=5,
            )
            self.send_clip_second_watched(
                streamer, clip, play_session_id, seconds_watched=seconds_watched
            )
            seconds_watched += 5

        return not streamer.missing_weekly_reward()

    def send_vod_minutes_watched(self, streamer: Streamer, vod_id: str):
        return self.send_spade_payload(
            streamer,
            payload=[
                {
                    "event": "minute-watched",
                    "properties": {
                        "channel_id": streamer.channel_id,
                        "broadcast_id": None,
                        "player": "site",
                        "user_id": self.client_session.login.get_user_id(),
                        "live": False,
                        "channel": streamer.username,
                        "vod_id": vod_id,
                        "content_mode": "vod",
                    },
                }
            ],
            name="VOD minute watched",
        )

    def simulate_vod_playback(
        self, streamer: Streamer, vod: VideoEdge, max_watch_seconds: float = 8 * 60
    ):
        """
        Simulates the user watching a VOD.
        :param streamer: The Streamer for whom to watch a VOD.
        :param vod: The VOD to watch.
        :param max_watch_seconds: The maximum number of seconds to simulate watching.
        :return: True if the playback was successful, False otherwise.
        """
        logger.info(
            f"Simulating VOD playback for {streamer} for up to {max_watch_seconds} seconds",
            extra={"emoji": ":clapper_board:"},
        )

        # Ensure we have the spade url
        if streamer.stream.spade_url is None:
            self.get_spade_url(streamer)
        if streamer.stream.spade_url is None:
            logger.debug(f"Unable to get Spade URL for {streamer}")
            return False

        # Watch the VOD
        accepted = 0
        overall_start_time = time.monotonic()
        watch_interval = 60
        while self.running and time.monotonic() - overall_start_time <= max_watch_seconds:
            # TODO make condition a Callable arg to make it more generically usable
            if not streamer.missing_weekly_reward():
                return True
            start_time = time.monotonic()
            if self.send_vod_minutes_watched(streamer, vod.id):
                accepted += 1
                request_duration = time.monotonic() - start_time
                interruptible_sleep(
                    lambda: self.running and streamer.missing_weekly_reward(),
                    duration=max(1, watch_interval - request_duration),
                )
            else:
                request_duration = time.monotonic() - start_time
                # Shorter sleep to try and pick it back up sooner
                interruptible_sleep(
                    lambda: self.running, duration=max(1, 5 - request_duration)
                )

        logger.debug(
            f"Sent {accepted} VOD watch requests for {streamer} over {max_watch_seconds} minutes"
        )
        return False

    def update_weekly_reward(
        self, streamer: Streamer, notification: WeeklyRewards.Notification
    ):
        if streamer.weekly_rewards is None:
            logger.error(
                f"Unable to update weekly reward for {streamer}, no existing reward found"
            )
            return
        # TODO new Events type for this?
        current_tier = (
            notification.accumulated_weeks
            if notification.accumulated_weeks is not None
            else 0
        )
        emojis = [
            ":seedling:",
            ":potted_plant:",
            ":wilted_flower:",
            ":rose:",
            ":bouquet:",
        ]
        # Default emoji for if Twitch starts doing longer events
        emoji = emojis[current_tier] if current_tier < len(emojis) else ":calendar:"
        logger.info(
            f"Weekly Reward update for {streamer}: {notification.notification_type}. "
            + f"{notification.days_visited_this_week}/{notification.event_config.days_required_per_week} days visited this week.",
            extra={"emoji": emoji},
        )
        streamer.weekly_rewards.days_visited_this_week = (
            notification.days_visited_this_week
        )
        streamer.weekly_rewards.has_visited_today = True
        if not streamer.weekly_rewards.has_earned_weekly_reward_this_week:
            streamer.weekly_rewards.has_earned_weekly_reward_this_week = (
                notification.notification_type == "WEEK_COMPLETED"
            )
        streamer.weekly_rewards.accumulated_weeks = (
            notification.accumulated_weeks
            if notification.accumulated_weeks is not None
            else 0
        )
        streamer.weekly_rewards.current_reward.tier = notification.current_reward.tier
        streamer.weekly_rewards.current_reward.channel_points = (
            notification.current_reward.channel_points
        )
        streamer.weekly_rewards.current_reward.badge.set_id = (
            notification.current_reward.badge_set_id
        )
        streamer.weekly_rewards.current_reward.badge.version = (
            notification.current_reward.badge_version
        )
        streamer.weekly_rewards.event_config.days_required_per_week = (
            notification.event_config.days_required_per_week
        )

    def sync_weekly_rewards(self, streamers: list[Streamer]):
        """
        Syncs the current Weekly Rewards state for the given streamers.
        :param streamers: The Streamers to sync.
        """
        for streamer in streamers:
            if not streamer.settings.weekly_rewards:
                continue
            try:
                streamer.weekly_rewards = self.gql.weekly_rewards(streamer.channel_id)
            except RetryError as e:
                logger.error(
                    f"Error while trying to sync weekly rewards for {streamer}: {e}"
                )

    def sync_clips_and_vods(self, streamers: list[Streamer]):
        for streamer in streamers:
            if not streamer.settings.weekly_rewards:
                continue
            try:
                clips_response = self.gql.clips(streamer.username, limit=10)
                vods_response = self.gql.recent_broadcasts(streamer.username, limit=5)
                # Update the VOD viewable state
                vods = [Video(edge=edge.node) for edge in vods_response.videos.edges]
                streamer.clips = [clip.node for clip in clips_response.clips.edges]
                streamer.vods = vods
            except RetryError as e:
                logger.error(
                    f"Error while trying to sync weekly rewards for {streamer}: {e}"
                )
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

    def initialize_streamers_context(
        self, streamers: list[Streamer], max_workers=10
    ) -> set[str]:
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

    @staticmethod
    def update_gift_sub(
        streamer: Streamer, gift_sub: GiftSub | None, send_event: bool = True
    ):
        """
        Updates the given Streamer with the given gift-sub, logs an Event if it has changed and `send_event` is True.
        :param streamer: The Streamer to update.
        :param gift_sub: The gift sub.
        :param send_event: If True an Event will be logged.
        """
        old_gift_sub = streamer.gift_sub
        if old_gift_sub == gift_sub:
            logger.debug(f"{streamer} gift sub unchanged: {gift_sub}")
        else:
            streamer.gift_sub = gift_sub
            extra: dict = {
                "emoji": ":wrapped_gift:",
            }
            if gift_sub is None:
                logger.info(f"Gift Sub to {streamer} has expired", extra=extra)
            else:
                if send_event:
                    extra["event"] = Events.GIFT_SUB_RECEIVED
                logger.info(gift_sub.describe(), extra=extra)

    def check_gift_sub(self, streamer: Streamer, send_event: bool = True):
        """
        Checks the gift-sub state for the given Streamer.
        :param streamer: The Streamer to update.
        :param send_event: If True an Event will be logged.
        """
        found_gift_sub = None
        try:
            gift_subs = self.gql.gift_subs()
        except RetryError as e:
            logger.error(f"Error while syncing gift subs: {e}")
            return

        for gift_sub in gift_subs:
            if gift_sub.target.id == streamer.channel_id:
                found_gift_sub = gift_sub
                break
        self.update_gift_sub(streamer, found_gift_sub, send_event)

    def check_gift_subs(self, streamers: list[Streamer], send_event: bool = True):
        """
        Checks the gift-sub state for all Streamers.
        :param streamers: The Streamers to update.
        :param send_event: If True an Event will be logged.
        """
        try:
            gift_subs = self.gql.gift_subs()
        except RetryError as e:
            logger.error(f"Error while syncing gift subs: {e}")
            return

        for gift_sub in gift_subs:
            streamer = next(
                (
                    streamer
                    for streamer in streamers
                    if streamer.channel_id == gift_sub.target.id
                ),
                None,
            )
            if streamer is not None:
                self.update_gift_sub(streamer, gift_sub, send_event)
            else:
                logger.debug(f"No Streamer found for Gift Sub {gift_sub.target}")

    def sync_gift_subs(
        self, streamers: list[Streamer], period_seconds: int, step: float = 1.0
    ):
        """
        Repeating task that synchronises gift subs. Stops once `self.running` is False.
        :param streamers: The Streamers to synd.
        :param period_seconds: The amount of time, in seconds, between syncs.
        :param step: The interval between checking if the task should run.
        """
        first_run = True
        while self.running:
            self.check_gift_subs(streamers, not first_run)
            if first_run:
                first_run = False
            interruptible_sleep(lambda: self.running, period_seconds, step)
