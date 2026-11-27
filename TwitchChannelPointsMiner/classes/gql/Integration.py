import logging
from typing import Callable, Any, Literal, Protocol, Tuple

import requests
from requests import Response

from TwitchChannelPointsMiner.JsonParser import InvalidJsonShapeError
from TwitchChannelPointsMiner.classes.ClientSession import ClientSession
from TwitchChannelPointsMiner.classes.Settings import FollowersOrder, Settings
from TwitchChannelPointsMiner.classes.entities.GiftSub import GiftSub
from TwitchChannelPointsMiner.classes.gql.Errors import (
    GQLError,
    RetryError,
)
from TwitchChannelPointsMiner.classes.gql.data.Parser import Parser, JsonParentContext
from TwitchChannelPointsMiner.classes.gql.data.response.ChannelPointsContext import (
    ChannelPointsContextResponse,
    UserPointsContributionResponse,
    ContributeToCommunityGoalResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.ChatRoomBanStatus import (
    ChatRoomBanStatusResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropsHighlightServiceAvailableDropsResponse,
    InventoryResponse,
    ViewerDropsDashboardResponse,
    DropCampaignDetailsResponse,
    DropsPageClaimDropsResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.GetIdFromLogin import (
    GetIdFromLoginResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.PlaybackAccessToken import (
    PlaybackAccessTokenResponse,
    VideoPlaybackAccessToken,
)
from TwitchChannelPointsMiner.classes.gql.data.response.Predictions import (
    MakePredictionResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.RewardList import (
    RewardListResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.VideoPlayerStreamInfoOverlayChannel import (
    VideoPlayerStreamInfoOverlayChannelResponse,
)
from TwitchChannelPointsMiner.constants import GQLOperations, CLIENT_ID
from TwitchChannelPointsMiner.utils import create_chunks
from TwitchChannelPointsMiner.utils.AttemptStrategy import (
    SuccessResult,
    ErrorResult,
    AttemptStrategy,
)
from TwitchChannelPointsMiner.classes.gql.data.request.Query import GQLQuery, operations

logger = logging.getLogger(__name__)


def validate_response(value: Any):
    """
    Validates a parsed response from the GQL API.
    :param value: The response.
    """
    return


def is_recoverable_error(e: Exception) -> bool:
    """
    Returns whether the given exception is recoverable.
    :param e: The exception to check.
    :return: True if the exception is recoverable, False otherwise.
    """
    if isinstance(e, requests.exceptions.RequestException):
        return True
    if isinstance(e, GQLError):
        return e.recoverable()
    return False


def error_context(e: Exception) -> str | None:
    """
    Returns a context string (or None) for the given Error. GQLErrors are well understood and so don't need context,
    anything else is likely a bug and so does need context.
    :param e: The Exception to check.
    :return: The context string, or None if no context is needed.
    """
    return None


def parse_list[T](parse: Callable[[Any], T], value: Any) -> list[T]:
    """
    Utility for parsing a list
    :param parse: Parser for the list item type.
    :param value: The value to parse.
    :return: The resultant list.
    :raises InvalidJsonShapeException: If the value is not a list.
    """
    if isinstance(value, list):
        result = []
        for index in range(len(value)):
            with JsonParentContext(index):
                result.append(parse(value[index]))
        return result
    raise InvalidJsonShapeError([], "list expected")


def parse_list_sub_parsers(parsers: list[Callable[[Any], Any]], value: Any) -> list:
    """
    Utility for parsing a list where each item is parsed using the subparser at the same index in the given list.
    :param parsers: The indexed list of subparsers.
    :param value: The value which should be a list of items parsable by the subparsers.
    :return: The resultant list.
    :raises InvalidJsonShapeException: If the value is not a list or the value's length doesn't match the parser's
            length.
    """
    if isinstance(value, list):
        if len(value) != len(parsers):
            raise InvalidJsonShapeError(
                [],
                f"List length ({len(value)}) does not match parsers length ({len(parsers)})",
            )
        result = []
        for index in range(len(parsers)):
            with JsonParentContext(index):
                result.append(parsers[index](value[index]))
        return result
    raise InvalidJsonShapeError([], "list expected")


class PostRequest(Protocol):
    """For creating Type Hints for a function that posts GQL requests."""

    def __call__(
        self, url: str, json: dict | list, headers: dict[str, str]
    ) -> Response: ...


class GQL:
    """
    Integration with Twitch's Graph Query Language (GQL) API.
    """

    def __init__(
        self,
        client_session: ClientSession,
        attempt_strategy: AttemptStrategy | None = None,
        request_timeout: Tuple[float, float] | None = None,
        parser: Parser | None = None,
    ):
        self.client_session = client_session
        """The client session for making requests."""
        self.attempt_strategy = (
            attempt_strategy
            if attempt_strategy is not None
            else AttemptStrategy(attempts=3, attempt_interval_seconds=1)
        )
        """Strategy for handling failed requests."""
        self.request_timeout = (
            request_timeout if request_timeout is not None else (3.05, 5)
        )
        """The timeouts for making GQL requests"""
        self.parser = Parser() if parser is None else parser
        """The parser for parsing GQL responses."""

    def __post_gql_request(
        self, request_json: dict | list[dict], redacted_request_json: dict | list[dict]
    ) -> Any:
        response = self.client_session.session.post(
            GQLOperations.url,
            json=request_json,
            headers={
                "Authorization": f"OAuth {self.client_session.login.get_auth_token()}",
                "Client-Id": CLIENT_ID,
                "Client-Session-Id": self.client_session.session_id,
                "Client-Version": self.client_session.version,
                "X-Device-Id": self.client_session.device_id,
            },
            timeout=self.request_timeout,
        )

        response_text = (
            "REDACTED" if Settings.logger.anonymiser.strict else response.text
        )

        logger.debug(
            f"Data: {redacted_request_json}, Status code: {response.status_code}, Content: {response_text}"
        )
        response.raise_for_status()
        return response.json()

    def __post_gql_request_single[T](
        self, request_json: dict, redacted_request_json: dict, parse: Callable[[Any], T]
    ):
        return parse(self.__post_gql_request(request_json, redacted_request_json))

    def __post_gql_request_batch[T](
        self,
        request_json: list[dict],
        redacted_request_json: list[dict],
        parser: Callable[[Any], T],
    ):
        response_json = self.__post_gql_request(request_json, redacted_request_json)
        if isinstance(response_json, list):
            return parse_list(parser, response_json)
        else:
            raise InvalidJsonShapeError(
                [], f"Expected batched response, got {type(response_json).__name__}"
            )

    def __post_gql_request_batch_mapped[T](
        self,
        request_json: list[dict],
        redacted_request_json: list[dict],
        parsers: list[Callable[[Any], Any]],
    ):
        response_json = self.__post_gql_request(request_json, redacted_request_json)
        if isinstance(response_json, list):
            return parse_list_sub_parsers(parsers, response_json)
        else:
            raise InvalidJsonShapeError(
                [], f"Expected batched response, got {type(response_json).__name__}"
            )

    @staticmethod
    def __handle_result[T](
        result: SuccessResult[T] | ErrorResult, operation_name: str
    ) -> T:
        if isinstance(result, ErrorResult):
            logger.debug(
                f"Unable to make {operation_name} request after {result.attempts} attempts."
            )
            raise RetryError(operation_name, result.errors)
        else:
            if result.attempts > 1:
                logger.debug(
                    f"{operation_name} succeeded after {result.attempts} attempts. Errors: {result.errors}"
                )
            return result.result

    def post_gql_request_single[T](
        self, prepared_query: GQLQuery, parse: Callable[[Any], T]
    ) -> T:
        """
        Posts the given GQL request. Handles automatic retries according to the `attempt_strategy`.
        :param prepared_query: The query data.
        :param parse: The function to use to parse the data.
        :return: The parsed response.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        result = self.attempt_strategy.make_attempts(
            lambda: self.__post_gql_request_single(
                prepared_query.data, prepared_query.redacted_data, parse
            ),
            validate_response,
            is_recoverable_error,
            error_context,
        )
        return self.__handle_result(result, prepared_query.name)

    def post_gql_request_batch[T](
        self, queries: list[GQLQuery], parser: Callable[[Any], T]
    ) -> list[T]:
        """
        Posts the given GQL request batch. Every item represents the same operation. Handles automatic retries according
        to the `attempt_strategy`.
        :param queries: The queries to send.
        :param parser: The function to use to parse each item in the response list.
        :return: The parsed response as a list.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        if len(queries) > 0:
            result = self.attempt_strategy.make_attempts(
                lambda: self.__post_gql_request_batch(
                    [query.data for query in queries],
                    [query.redacted_data for query in queries],
                    parser,
                ),
                validate_response,
                is_recoverable_error,
                error_context,
            )
            return self.__handle_result(result, f"Batch {queries[0].name}")
        return []

    def post_gql_request_batch_mapped(
        self,
        operation_names: list[str],
        request_json: list[dict],
        redacted_request_json: list[dict],
        parser: list[Callable[[Any], Any]],
    ) -> list:
        """
        Posts the given GQL request batch. Handles automatic retries according to the `attempt_strategy`.
        When the `parser` is a list we parse the response by matching the index of the parser to the index of each
        response item.
        :param operation_names: The names of each operation.
        :param request_json: The data to send as a list of the batched items.
        :param parser: The function(s) to use to parse the data.
        :return: The parsed response as a list.
        """
        result = self.attempt_strategy.make_attempts(
            lambda: self.__post_gql_request_batch_mapped(
                request_json, redacted_request_json, parser
            ),
            validate_response,
            is_recoverable_error,
            error_context,
        )
        return self.__handle_result(result, f"Batch {operation_names}")

    def video_player_stream_info_overlay_channel(
        self, streamer_username: str
    ) -> VideoPlayerStreamInfoOverlayChannelResponse:
        """
        Gets information about the streamer with the given username.
        :param streamer_username: The username of the streamer.
        :return: The information.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.video_player_stream_info_overlay_channel.prepare(
                channel=streamer_username
            ),
            self.parser.parse_video_player_stream_info_overlay_channel_data,
        )

    def get_id_from_login(self, streamer_username: str) -> GetIdFromLoginResponse:
        """
        Gets the user id from a Twitch user's login username.
        :param streamer_username: The username of the user.
        :return: The id or an empty string if the user doesn't exist.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.get_id_from_login.prepare(login=streamer_username),
            self.parser.parse_get_id_from_login_response,
        )

    def channel_follows(
        self, limit: int = 100, order: FollowersOrder = FollowersOrder.ASC
    ) -> list[str]:
        """
        Gets a list of logins for channels the user follows.
        :param limit: The maximum amount of followers to find per request.
        :param order: The order in which followers should be requested.
        :return: The list of followers, returns none if there was an error.
        :raises RetryError: If one or more errors occurred while attempting the request(s).
        """
        has_next = True
        last_cursor = ""
        follows: list[str] = []
        while has_next is True:
            parsed_response = self.post_gql_request_single(
                operations.channel_follows.prepare(
                    limit=limit, order=str(order), cursor=last_cursor
                ),
                self.parser.parse_channel_follows_response,
            )
            if parsed_response is not None:
                for edge in parsed_response.follows.edges:
                    follow = edge.node
                    follows.append(follow.login)
                    last_cursor = edge.cursor if edge.cursor is not None else ""
                has_next = parsed_response.follows.page_info.has_next_page
            else:
                logger.warning("Unable to get follower list.")
                return []
        return follows

    def join_raid(self, raid_id: str):
        """
        Joins the raid with the given id.
        :param raid_id: The id of the raid to join.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        self.post_gql_request_single(
            operations.join_raid.prepare(raid_id),
            self.parser.parse_join_raid_response,
        )

    def get_playback_access_token(self, username: str) -> PlaybackAccessTokenResponse:
        """
        Gets a playback access token for the streamer with the given username.
        :param username: The username of the streamer.
        :return: The playback access token.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.playback_access_token.prepare(login=username),
            self.parser.parse_playback_access_token_response,
        )

    def get_video_playback_access_token(
        self, username: str, vod_id: str
    ) -> VideoPlaybackAccessToken:
        """
        Gets a playback access token for the streamer with the given username.
        :param username: The username of the streamer.
        :param vod_id: The ID of the VOD to access, leave as None to access a Stream.
        :return: The playback access token.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.playback_access_token.prepare(
                login=username, vod_id=vod_id, is_vod=True, is_live=False
            ),
            self.parser.parse_vod_playback_access_token_response,
        )

    def get_channel_points_context(self, username: str) -> ChannelPointsContextResponse:
        """
        Gets the channel points context for the streamer with the given username.
        :param username: The username of the streamer.
        :return: The channel points context.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.channel_points_context.prepare(username),
            self.parser.parse_channel_points_context_response,
        )

    def make_prediction(
        self, event_id: str, outcome_id: str, points: int
    ) -> MakePredictionResponse:
        """
        Makes a prediction.
        :param event_id: The id of the prediction event.
        :param outcome_id: The id of the outcome on which to predict.
        :param points: The number of points to wager.
        :return: The response.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.make_prediction.prepare(
                event_id=event_id, outcome_id=outcome_id, points=points
            ),
            self.parser.parse_make_prediction_response,
        )

    def claim_community_points(self, channel_id: str, claim_id: str):
        """
        Claims the community points claim with the given id for the given channel.
        :param channel_id: The id of the channel of the claim.
        :param claim_id: The id of the claim.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        self.post_gql_request_single(
            operations.claim_community_points.prepare(
                channel_id=channel_id, claim_id=claim_id
            ),
            self.parser.parse_claim_community_points_response,
        )

    def claim_moment(self, moment_id: str):
        """
        Claims the moment of the given id.
        :param moment_id: The id of the moment to claim.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        self.post_gql_request_single(
            operations.community_moment_callout_claim.prepare(moment_id),
            self.parser.parse_community_moment_callout_claim_response,
        )

    def get_available_drops(
        self, channel_id: str
    ) -> DropsHighlightServiceAvailableDropsResponse:
        """
        Gets the ids of all drops that are available.
        :param channel_id: The id of the channel to check.
        :return: The response.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.drops_highlight_service_available_drops.prepare(channel_id),
            self.parser.parse_drops_highlight_service_available_drops,
        )

    def get_inventory(self) -> InventoryResponse:
        """
        Gets the user's Inventory.
        :return: The response.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.inventory.prepare(),
            self.parser.parse_inventory_response,
        )

    def get_viewer_drops_dashboard(self) -> ViewerDropsDashboardResponse:
        """
        Gets the viewer drops dashboard.
        :return: The response.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.viewer_drops_dashboard.prepare(),
            self.parser.parse_viewer_drops_dashboard_response,
        )

    def get_drop_campaign_details(
        self, campaign_ids: list[str]
    ) -> list[DropCampaignDetailsResponse]:
        """
        Gets the drop campaign details for the campaigns with the given ids.
        :param campaign_ids: The ids of the campaigns.
        :return: The response.
        :raises RetryError: If one or more errors occurred while attempting the request(s).
        """
        result = []
        # Batch the requests into chunks of 20
        chunks = create_chunks(campaign_ids, 20)
        for chunk in chunks:
            user_id = self.client_session.login.get_user_id()
            queries = [
                operations.drop_campaign_details.prepare(
                    drop_id=campaign, user_id=user_id
                )
                for campaign in chunk
            ]

            response = self.post_gql_request_batch(
                queries,
                self.parser.parse_drop_campaign_details_response,
            )

            if not isinstance(response, list):
                logger.debug("Unexpected campaigns response format, skipping chunk")
                continue
            for item in response:
                if item is not None:
                    result.append(item)
        return result

    def claim_drop_rewards(self, drop_instance_id: str) -> DropsPageClaimDropsResponse:
        """
        Claims the rewards for the drop with the given id.
        :param drop_instance_id: The id of the drop.
        :return: The response.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.drops_page_claim_drop_rewards.prepare(drop_instance_id),
            self.parser.parse_drop_page_claim_drop_rewards,
        )

    def get_user_points_contribution(
        self, username: str
    ) -> UserPointsContributionResponse:
        """
        Gets the user points contribution for streamer with the given username.
        :param username: The username of the streamer.
        :return: The response.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.user_points_contribution.prepare(username),
            self.parser.parse_user_points_contribution,
        )

    def contribute_to_community_goal(
        self, channel_id, goal_id, amount
    ) -> ContributeToCommunityGoalResponse:
        """
        Contributes the given amount of channel points to the given community goal.
        :param channel_id: The id of the channel running the goal.
        :param goal_id: The id of the goal.
        :param amount: The amount to contribute.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.contribute_community_points_community_goal.prepare(
                amount=amount, channel_id=channel_id, goal_id=goal_id
            ),
            self.parser.parse_contribute_community_points_community_goal,
        )

    def with_is_stream_live_query(self, channel_id: str):
        """
        Gets basic information about the current stream.
        :param channel_id: The id of the channel to check.
        :return: The response.
        :raises RetryError: If one or more errors occurred while attempting the request.
        """
        return self.post_gql_request_single(
            operations.with_is_stream_live.prepare(channel_id),
            self.parser.parse_with_is_stream_live_query,
        )

    def reward_list(self, channel_id: str) -> RewardListResponse:
        """
        Gets the user's Rewards for the given channel. Useful for getting info on watch streak milestones.
        :param channel_id: The id of the channel.
        :return: The response.
        """
        return self.post_gql_request_single(
            operations.reward_list.prepare(channel_id),
            self.parser.parse_reward_list,
        )

    def chat_room_ban_status(
        self, user_id: int, channel_id: str
    ) -> ChatRoomBanStatusResponse:
        """
        Gets the user's chat room ban status for the given channel.
        :param user_id: The id of the user.
        :param channel_id: The id of the channel.
        :return: The response.
        """
        return self.post_gql_request_single(
            operations.chat_room_ban_status.prepare(
                user_id=user_id, channel_id=channel_id
            ),
            self.parser.parse_chat_room_ban_status,
        )

    def gift_subs(self, limit: int = 100) -> list[GiftSub]:
        """
        Gets the user's gift subs.
        :param limit: The maximum number of subs to acquire per request.
        :return: The gift sub(s).
        """
        has_next = True
        last_cursor = ""
        gift_subs: list[GiftSub] = []
        while has_next:
            parsed_response = self.post_gql_request_single(
                operations.subscriptions_management_subscription_benefits.prepare(
                    cursor=last_cursor, limit=limit
                ),
                self.parser.parse_subscriptions_management_subscription_benefits,
            )
            for edge in parsed_response.pages.edges:
                gift_subs.append(edge.node)
                last_cursor = edge.cursor if edge.cursor is not None else ""
            has_next = parsed_response.pages.page_info.has_next_page
        return gift_subs

    def weekly_rewards(self, channel_id: str):
        return self.post_gql_request_single(
            operations.weekly_visit_rewards_query.prepare(channel_id),
            self.parser.parse_weekly_rewards,
        )

    def recent_broadcasts(self, channel_login: str, limit: int):
        return self.post_gql_request_single(
            operations.filterable_video_tower_videos.prepare(
                channel_owner_login=channel_login, limit=limit
            ),
            self.parser.parse_filterable_video_tower_videos,
        )

    def clips(
        self,
        channel_login: str,
        limit: int = 20,
        _filter: Literal[
            "ALL_TIME", "LAST_MONTH", "LAST_WEEK", "LAST_DAY"
        ] = "ALL_TIME",
    ):
        return self.post_gql_request_single(
            operations.clips_cards_user.prepare(
                login=channel_login, limit=limit, _filter=_filter
            ),
            self.parser.parse_clips_cards_user,
        )

    def drop_channel_campaigns_progress(self, channel_id: str):
        return self.post_gql_request_single(
            operations.drop_channel_campaigns_progress.prepare(channel_id),
            self.parser.parse_drop_channel_campaigns_progress,
        )


class GQLFactory:
    """Factory class for creating GQL objects."""

    def __init__(
        self,
        parser: Parser | None = None,
    ):
        self.parser = parser

    def create(
        self,
        client_session: ClientSession,
        strategy: AttemptStrategy | None,
        request_timeout: Tuple[float, float] | None = None,
    ) -> GQL:
        """
        Creates a new GQL instance.
        :param client_session: The ClientSession for the instance.
        :param strategy: The Attempt Strategy to use.
        :return: The instance.
        """
        return GQL(
            client_session=client_session,
            attempt_strategy=strategy,
            parser=self.parser,
            request_timeout=request_timeout,
        )
