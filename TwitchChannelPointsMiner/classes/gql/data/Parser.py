from typing import Callable, Any

from TwitchChannelPointsMiner.JsonParser import (
    InvalidJsonShapeError,
    expect_int,
    expect_str,
    describe_value,
    expect_dict,
    parse_expected_value,
    parse_value,
    list_parser,
    expect_bool,
    optional_parser,
    expect_iso_8601,
    expect_list,
    JsonParentContext,
    dig,
    expect_any,
)
from TwitchChannelPointsMiner.classes.entities.GiftSub import GiftSub, Gifter, Target
from TwitchChannelPointsMiner.classes.gql.Errors import (
    GQLResponseErrors,
)
from TwitchChannelPointsMiner.classes.gql.data.response import (
    ChannelPointsContext,
    Predictions,
    Drops,
    PlaybackAccessToken,
    SubscriptionManagement,
    WeeklyRewards,
    WithIsStreamLiveQuery,
    RewardList,
    FilterableVideoTower,
    ClipsCardsUser,
)
from TwitchChannelPointsMiner.classes.gql.data.response.BroadcastSettings import (
    BroadcastSettings,
    GameBroadcastSettings,
)
from TwitchChannelPointsMiner.classes.gql.data.response.ChannelFollows import (
    ChannelFollowsResponse,
    Follow,
)
from TwitchChannelPointsMiner.classes.gql.data.response.ChannelPointsContext import (
    ChannelPointsContextResponse,
    ContributeToCommunityGoalResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.ChatRoomBanStatus import (
    ChatRoomBanStatusResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.Drops import (
    DropsHighlightServiceAvailableDropsResponse,
    InventoryResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.Error import Error
from TwitchChannelPointsMiner.classes.gql.data.response.GetIdFromLogin import (
    GetIdFromLoginResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.Pagination import (
    PageInfo,
    Paginated,
    Edge,
)
from TwitchChannelPointsMiner.classes.gql.data.response.PlaybackAccessToken import (
    PlaybackAccessTokenResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.RewardList import (
    RewardListResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.Stream import Stream, Tag
from TwitchChannelPointsMiner.classes.gql.data.response.VideoPlayerStreamInfoOverlayChannel import (
    User,
    VideoPlayerStreamInfoOverlayChannelResponse,
)
from TwitchChannelPointsMiner.classes.gql.data.response.WithIsStreamLiveQuery import (
    WithIsStreamLiveQueryResponse,
)

# Parsers for GQL response types


def error_path_item_parser(value: Any) -> str | int:
    try:
        return expect_int(value)
    except InvalidJsonShapeError:
        try:
            return expect_str(value)
        except InvalidJsonShapeError:
            raise InvalidJsonShapeError(
                [], f"string or int expected, got {describe_value(value)}"
            )


def error_parser(value: Any) -> Error:
    expect_dict(value)
    message = parse_expected_value(value, "message", expect_str)
    recoverable = message in [
        "service timeout",
        "service unavailable",
        "context deadline exceeded",
        "PersistedQueryUnavailable",
    ]
    return Error(
        recoverable,
        message,
        parse_value(value, "path", list_parser(error_path_item_parser)),
    )


def page_info_parser(value: Any) -> PageInfo:
    return PageInfo(
        has_next_page=parse_expected_value(value, "hasNextPage", expect_bool),
        start_cursor=parse_value(value, "startCursor", expect_str),
        end_cursor=parse_value(value, "endCursor", expect_str),
    )


def paginated_parser[T](
    value_parser: Callable[[Any], T],
) -> Callable[[Any], Paginated[T]]:
    """
    Gets a parser for Paginated values.
    :param value_parser: The parser for the `node` of the paginated data.
    :return: The Paginated data.
    """

    def edge_parser(edge: Any) -> Edge[T]:
        cursor = parse_expected_value(edge, "cursor", optional_parser(expect_str))
        node = parse_expected_value(edge, "node", value_parser)
        return Edge(cursor, node)

    def inner_parser(container: Any) -> Paginated[T]:
        edges = parse_expected_value(container, "edges", list_parser(edge_parser))
        page_info = parse_expected_value(container, "pageInfo", page_info_parser)
        return Paginated(edges, page_info)

    return inner_parser


def tag_parser(value: Any) -> Tag:
    expect_dict(value)
    return Tag(
        _id=parse_expected_value(value, "id", expect_str),
        localized_name=parse_expected_value(value, "localizedName", expect_str),
    )


def game_parser(value: Any) -> GameBroadcastSettings:
    expect_dict(value)
    return GameBroadcastSettings(
        _id=parse_expected_value(value, "id", expect_str),
        display_name=parse_expected_value(value, "displayName", expect_str),
        name=parse_expected_value(value, "name", expect_str),
    )


def broadcast_settings_parser(value: Any) -> BroadcastSettings:
    expect_dict(value)
    return BroadcastSettings(
        _id=parse_expected_value(value, "id", expect_str),
        title=parse_expected_value(value, "title", expect_str),
        game=parse_expected_value(value, "game", optional_parser(game_parser)),
    )


def stream_parser(value: Any) -> Stream:
    expect_dict(value)
    return Stream(
        _id=parse_expected_value(value, "id", expect_str),
        viewers_count=parse_expected_value(value, "viewersCount", expect_int),
        tags=parse_expected_value(value, "tags", list_parser(tag_parser)),
    )


def user_parser(value: Any) -> User:
    expect_dict(value)
    _id = parse_expected_value(value, "id", expect_str)
    profile_url = parse_expected_value(value, "profileURL", expect_str)
    display_name = parse_expected_value(value, "displayName", expect_str)
    login = parse_expected_value(value, "login", expect_str)
    profile_image_url = parse_expected_value(value, "profileImageURL", expect_str)
    broadcast_settings = parse_expected_value(
        value, "broadcastSettings", broadcast_settings_parser
    )
    stream = parse_value(value, "stream", optional_parser(stream_parser))
    return User(
        _id=_id,
        profile_url=profile_url,
        display_name=display_name,
        login=login,
        profile_image_url=profile_image_url,
        broadcast_settings=broadcast_settings,
        stream=stream,
    )


def follow_self_follower_parser(value: Any) -> Follow.SelfEdge.Follower:
    expect_dict(value)
    return Follow.SelfEdge.Follower(
        disable_notifications=parse_expected_value(
            value, "disableNotifications", expect_bool
        ),
        followed_at=parse_expected_value(value, "followedAt", expect_iso_8601),
    )


def follow_self_edge_parser(value: Any) -> Follow.SelfEdge:
    expect_dict(value)
    return Follow.SelfEdge(
        can_follow=parse_expected_value(value, "canFollow", expect_bool),
        follower=parse_expected_value(value, "follower", follow_self_follower_parser),
    )


def follow_parser(value: Any) -> Follow:
    expect_dict(value)
    return Follow(
        _id=parse_expected_value(value, "id", expect_str),
        banner_image_url=parse_expected_value(
            value, "bannerImageURL", optional_parser(expect_str)
        ),
        display_name=parse_expected_value(value, "displayName", expect_str),
        login=parse_expected_value(value, "login", expect_str),
        profile_image_url=parse_expected_value(value, "profileImageURL", expect_str),
        _self=parse_expected_value(value, "self", follow_self_edge_parser),
    )


def authorization_parser(value: Any) -> PlaybackAccessToken.Authorization:
    expect_dict(value)
    return PlaybackAccessToken.Authorization(
        is_forbidden=parse_expected_value(value, "isForbidden", expect_bool),
        forbidden_reason_code=parse_expected_value(
            value, "forbiddenReasonCode", expect_str
        ),
    )


def claim_parser(value: Any) -> ChannelPointsContext.Properties.Claim:
    expect_dict(value)
    return ChannelPointsContext.Properties.Claim(
        _id=parse_expected_value(value, "id", expect_str),
    )


def multiplier_parser(value: Any) -> ChannelPointsContext.Properties.Multiplier:
    expect_dict(value)
    return ChannelPointsContext.Properties.Multiplier(
        factor=parse_expected_value(value, "factor", float),
    )


def community_points_parser(value: Any) -> ChannelPointsContext.Properties:
    expect_dict(value)
    return ChannelPointsContext.Properties(
        available_claim=parse_expected_value(
            value, "availableClaim", optional_parser(claim_parser)
        ),
        balance=parse_expected_value(value, "balance", expect_int),
        active_multipliers=parse_expected_value(
            value, "activeMultipliers", list_parser(multiplier_parser)
        ),
    )


def channel_self_edge_parser(
    value: Any,
) -> ChannelPointsContext.Channel.ChannelSelfEdge:
    expect_dict(value)
    return ChannelPointsContext.Channel.ChannelSelfEdge(
        community_points=parse_expected_value(
            value, "communityPoints", community_points_parser
        ),
    )


def community_goal_parser(value: Any) -> ChannelPointsContext.CommunityGoal:
    expect_dict(value)
    return ChannelPointsContext.CommunityGoal(
        amount_needed=parse_expected_value(value, "amountNeeded", expect_int),
        _id=parse_expected_value(value, "id", expect_str),
        is_in_stock=parse_expected_value(value, "isInStock", expect_bool),
        per_stream_user_maximum_contribution=parse_expected_value(
            value, "perStreamUserMaximumContribution", expect_int
        ),
        points_contributed=parse_expected_value(value, "pointsContributed", expect_int),
        status=parse_expected_value(value, "status", expect_str),
        title=parse_expected_value(value, "title", expect_str),
    )


def community_points_settings_parser(
    value: Any,
) -> ChannelPointsContext.CommunityPointsSettings:
    expect_dict(value)
    return ChannelPointsContext.CommunityPointsSettings(
        is_enabled=parse_expected_value(value, "isEnabled", expect_bool),
        goals=parse_expected_value(value, "goals", list_parser(community_goal_parser)),
    )


def channel_parser(value: Any) -> ChannelPointsContext.Channel:
    expect_dict(value)
    return ChannelPointsContext.Channel(
        _id=parse_expected_value(value, "id", expect_str),
        edge=parse_expected_value(value, "self", channel_self_edge_parser),
        community_points_settings=parse_expected_value(
            value, "communityPointsSettings", community_points_settings_parser
        ),
    )


def community_parser(value: Any) -> ChannelPointsContext.CommunityUser:
    expect_dict(value)
    return ChannelPointsContext.CommunityUser(
        _id=parse_expected_value(value, "id", expect_str),
        display_name=parse_expected_value(value, "displayName", expect_str),
        channel=parse_expected_value(value, "channel", channel_parser),
    )


def prediction_error_parser(value: Any) -> Predictions.Error:
    expect_dict(value)
    return Predictions.Error(
        code=parse_expected_value(value, "code", expect_str),
    )


def time_based_drop_self_edge_parser(
    value: Any,
) -> Drops.TimeBasedDropInProgress.SelfEdge:
    expect_dict(value)
    return Drops.TimeBasedDropInProgress.SelfEdge(
        has_preconditions_met=parse_expected_value(
            value, "hasPreconditionsMet", expect_bool
        ),
        current_minutes_watched=parse_expected_value(
            value, "currentMinutesWatched", expect_int
        ),
        current_subs=parse_expected_value(value, "currentSubs", expect_int),
        drop_instance_id=parse_expected_value(
            value, "dropInstanceID", optional_parser(expect_str)
        ),
        is_claimed=parse_expected_value(value, "isClaimed", expect_bool),
    )


def drop_benefits_parser(value: Any) -> list[str]:
    expect_list(value)
    benefits = []
    for index, edge in enumerate(value):
        with JsonParentContext(index):
            benefit = parse_expected_value(edge, "benefit", expect_dict)
            with JsonParentContext("benefit"):
                benefits.append(parse_expected_value(benefit, "name", expect_str))
    return benefits


def time_based_drop_details_parser(value: Any) -> Drops.TimeBasedDropDetails:
    expect_dict(value)
    return Drops.TimeBasedDropDetails(
        _id=parse_expected_value(value, "id", expect_str),
        name=parse_expected_value(value, "name", expect_str),
        end_at=parse_expected_value(value, "endAt", expect_iso_8601),
        start_at=parse_expected_value(value, "startAt", expect_iso_8601),
        benefits=parse_expected_value(value, "benefitEdges", drop_benefits_parser),
        required_minutes_watched=parse_expected_value(
            value, "requiredMinutesWatched", expect_int
        ),
        required_subs=parse_expected_value(value, "requiredSubs", expect_int),
    )


def drop_campaign_dashboard_parser(value: Any) -> Drops.DropCampaignDashboard:
    expect_dict(value)
    return Drops.DropCampaignDashboard(
        _id=parse_expected_value(value, "id", expect_str),
        status=parse_expected_value(value, "status", expect_str),
    )


def drops_game_details_parser(value: Any) -> Drops.GameDetails:
    expect_dict(value)
    return Drops.GameDetails(
        _id=parse_expected_value(value, "id", expect_str),
        slug=parse_expected_value(value, "slug", expect_str),
        display_name=parse_expected_value(value, "displayName", expect_str),
    )


def time_based_drop_in_progress_parser(value: Any) -> Drops.TimeBasedDropInProgress:
    expect_dict(value)
    return Drops.TimeBasedDropInProgress(
        _id=parse_expected_value(value, "id", expect_str),
        name=parse_expected_value(value, "name", expect_str),
        end_at=parse_expected_value(value, "endAt", expect_iso_8601),
        start_at=parse_expected_value(value, "startAt", expect_iso_8601),
        benefits=parse_expected_value(value, "benefitEdges", drop_benefits_parser),
        required_minutes_watched=parse_expected_value(
            value, "requiredMinutesWatched", expect_int
        ),
        required_subs=parse_expected_value(value, "requiredSubs", expect_int),
        self_edge=parse_expected_value(value, "self", time_based_drop_self_edge_parser),
    )


def drop_campaign_in_progress_parser(value: Any) -> Drops.DropCampaignInProgress:
    expect_dict(value)
    return Drops.DropCampaignInProgress(
        _id=parse_expected_value(value, "id", expect_str),
        time_based_drops=parse_expected_value(
            value, "timeBasedDrops", list_parser(time_based_drop_in_progress_parser)
        ),
    )


def drop_campaign_details_parser(value: Any) -> Drops.DropCampaignDetails:
    expect_dict(value)
    allow = parse_expected_value(value, "allow", expect_dict)
    # We only want the ids of allow channels, if they exist
    allow_channel_ids: list[str] | None = None
    with JsonParentContext("allow"):
        channels = parse_expected_value(allow, "channels", optional_parser(expect_list))
        if channels is not None:
            allow_channel_ids = []
            with JsonParentContext("channels"):
                for index, channel in enumerate(channels):
                    with JsonParentContext(index):
                        allow_channel_ids.append(
                            parse_expected_value(channel, "id", expect_str)
                        )
    return Drops.DropCampaignDetails(
        _id=parse_expected_value(value, "id", expect_str),
        name=parse_expected_value(value, "name", expect_str),
        status=parse_expected_value(value, "status", expect_str),
        game=parse_expected_value(value, "game", drops_game_details_parser),
        allow_channel_ids=allow_channel_ids,
        start_at=parse_expected_value(value, "startAt", expect_iso_8601),
        end_at=parse_expected_value(value, "endAt", expect_iso_8601),
        time_based_drops=parse_expected_value(
            value, "timeBasedDrops", list_parser(time_based_drop_details_parser)
        ),
    )


def goal_contribution_parser(value: Any) -> ChannelPointsContext.GoalContribution:
    expect_dict(value)
    goal = parse_expected_value(value, "goal", expect_dict)
    with JsonParentContext("goal"):
        goal_id = parse_expected_value(goal, "id", expect_str)

    return ChannelPointsContext.GoalContribution(
        _id=goal_id,
        user_points_contributed_this_stream=parse_expected_value(
            value, "userPointsContributedThisStream", expect_int
        ),
    )


def with_is_stream_live_query_stream_parser(value: Any) -> WithIsStreamLiveQuery.Stream:
    expect_dict(value)
    return WithIsStreamLiveQuery.Stream(
        _id=parse_expected_value(value, "id", expect_str),
        created_at=parse_expected_value(value, "createdAt", expect_iso_8601),
    )


def with_is_stream_live_query_user_parser(value: Any) -> WithIsStreamLiveQuery.User:
    expect_dict(value)
    return WithIsStreamLiveQuery.User(
        _id=parse_expected_value(value, "id", expect_str),
        stream=parse_expected_value(
            value, "stream", optional_parser(with_is_stream_live_query_stream_parser)
        ),
    )


def reward_list_viewer_milestone_parser(value: Any) -> RewardList.ViewerMilestone:
    expect_dict(value)
    return RewardList.ViewerMilestone(
        _id=parse_expected_value(value, "id", expect_str),
        value=parse_expected_value(value, "value", expect_str),
        achievement_timestamp=parse_expected_value(
            value, "achievementTimestamp", optional_parser(expect_iso_8601)
        ),
        share_status=parse_expected_value(value, "shareStatus", expect_str),
    )


def reward_list_watch_streak_milestone_parser(
    value: Any,
) -> RewardList.WatchStreakMilestone:
    expect_dict(value)
    return RewardList.WatchStreakMilestone(
        viewer_milestone=parse_expected_value(
            value, "watchStreakMilestone", reward_list_viewer_milestone_parser
        ),
        threshold=parse_expected_value(value, "watchStreakThreshold", expect_int),
        copo_bonus=parse_expected_value(value, "watchStreakCopoBonus", expect_int),
        state=parse_expected_value(value, "state", expect_str),
        expires_at=parse_expected_value(
            value, "expiresAt", optional_parser(expect_iso_8601)
        ),
    )


def reward_list_channel_self_parser(value: Any) -> RewardList.Channel.SelfEdge:
    expect_dict(value)
    return RewardList.Channel.SelfEdge(
        watch_streak_milestone=parse_expected_value(
            value, "watchStreakMilestone", reward_list_watch_streak_milestone_parser
        )
    )


def reward_list_channel_parser(value: Any) -> RewardList.Channel:
    expect_dict(value)
    _id = parse_expected_value(value, "id", expect_str)
    return RewardList.Channel(
        _id=_id,
        _self=parse_expected_value(value, "self", reward_list_channel_self_parser),
    )


def subscription_benefit_parser(value) -> GiftSub:
    value = expect_dict(value)
    gift = parse_expected_value(value, "gift", expect_dict)
    with JsonParentContext("gift"):
        gifter_dict = parse_expected_value(gift, "gifter", optional_parser(expect_dict))
        if gifter_dict is None:
            gifter = None
        else:
            with JsonParentContext("gifter"):
                gifter = Gifter(
                    _id=parse_expected_value(gifter_dict, "id", expect_str),
                    username=parse_expected_value(gifter_dict, "login", expect_str),
                    display_name=parse_expected_value(
                        gifter_dict, "displayName", expect_str
                    ),
                )

    user = parse_expected_value(value, "user", expect_dict)
    with JsonParentContext("user"):
        target = Target(
            _id=parse_expected_value(user, "id", expect_str),
            username=parse_expected_value(user, "login", expect_str),
            display_name=parse_expected_value(user, "displayName", expect_str),
        )

    # Tier = "1000"/"2000"/"3000"
    tier = parse_expected_value(value, "tier", expect_str)
    tier = int(tier[0])

    # TODO I don't have an example of a multi-month gift sub
    ends_at = parse_expected_value(value, "endsAt", expect_iso_8601)

    return GiftSub(
        _id=parse_expected_value(value, "id", expect_str),
        target=target,
        gifter=gifter,
        tier=tier,
        ends_at=ends_at,
    )


# Weekly Rewards
def weekly_rewards_badge_parser(value) -> WeeklyRewards.Badge:
    value = expect_dict(value)
    return WeeklyRewards.Badge(
        _id=parse_expected_value(value, "id", expect_str),
        set_id=parse_expected_value(value, "setID", expect_str),
        version=parse_expected_value(value, "version", expect_str),
        title=parse_expected_value(value, "title", expect_str),
        image_1x=parse_expected_value(value, "image1x", expect_str),
        image_2x=parse_expected_value(value, "image2x", expect_str),
        image_4x=parse_expected_value(value, "image4x", expect_str),
        click_action=parse_expected_value(value, "clickAction", expect_str),
        click_url=parse_expected_value(value, "clickURL", expect_str),
    )


def weekly_rewards_tier_parser(value) -> WeeklyRewards.RewardTier:
    value = expect_dict(value)
    return WeeklyRewards.RewardTier(
        tier=parse_expected_value(value, "tier", expect_int),
        channel_points=parse_expected_value(value, "channelPoints", expect_int),
        badge=parse_expected_value(value, "badge", weekly_rewards_badge_parser),
    )


def weekly_rewards_event_config_parser(value) -> WeeklyRewards.EventConfig:
    value = expect_dict(value)
    return WeeklyRewards.EventConfig(
        _id=parse_expected_value(value, "id", expect_str),
        days_required_per_week=parse_expected_value(
            value, "daysRequiredPerWeek", expect_int
        ),
        end_date=parse_expected_value(value, "endDate", expect_iso_8601),
        week_reset_dates=parse_expected_value(
            value, "weekResetDates", list_parser(expect_iso_8601)
        ),
        reward_tiers=parse_expected_value(
            value, "rewardTiers", list_parser(weekly_rewards_tier_parser)
        ),
    )


def weekly_visit_rewards_parser(value) -> WeeklyRewards.WeeklyRewards:
    value = expect_dict(value)
    return WeeklyRewards.WeeklyRewards(
        days_visited_this_week=parse_expected_value(
            value, "daysVisitedThisWeek", expect_int
        ),
        accumulated_weeks=parse_expected_value(value, "accumulatedWeeks", expect_int),
        has_earned_weekly_reward_this_week=parse_expected_value(
            value, "hasEarnedWeeklyRewardThisWeek", expect_bool
        ),
        has_visited_today=parse_expected_value(value, "hasVisitedToday", expect_bool),
        current_reward=parse_expected_value(
            value, "currentReward", weekly_rewards_tier_parser
        ),
        event_config=parse_expected_value(
            value, "eventConfig", weekly_rewards_event_config_parser
        ),
    )


# VODs


def filterable_video_tower_video_edge_parser(value) -> FilterableVideoTower.VideoEdge:
    value = expect_dict(value)
    return FilterableVideoTower.VideoEdge(
        _id=parse_expected_value(value, "id", expect_str),
        broadcast_id=dig(value, ["broadcastIdentifier", "id"], expect_str),
        length_seconds=parse_expected_value(value, "lengthSeconds", expect_int),
    )


# Clips


def clips_cards_user_clip_edge_parser(value) -> ClipsCardsUser.Clip:
    value = expect_dict(value)
    return ClipsCardsUser.Clip(
        _id=parse_expected_value(value, "id", expect_str),
        slug=parse_expected_value(value, "slug", expect_str),
        url=parse_expected_value(value, "url", expect_str),
        title=parse_expected_value(value, "title", expect_str),
        duration_seconds=parse_expected_value(value, "durationSeconds", expect_int),
    )


class Parser:
    """Class that can parse responses from the Twitch GQL API."""

    def parse_base_response(
        self, response: Any, expect_no_errors: bool
    ) -> tuple[list[Error], str, dict]:
        """
        Minimal parser for a base GQL response. Gets the `errors` and `data` fields and the `operationName` in
        `extensions`.
        :param response: The response to parse.
        :param expect_no_errors: Whether to expect errors.
        :return: A tuple of a list of any errors, the operation name, and the data dict.
        :raises GQLResponseErrors: If `expect_no_errors` is True and errors were found.
        """
        response_dict = expect_dict(response)
        if response_dict == {}:
            raise InvalidJsonShapeError([], "response was empty")
        errors = parse_value(response_dict, "errors", list_parser(error_parser), [])
        data = parse_value(response_dict, "data", expect_dict)
        extensions = parse_expected_value(response_dict, "extensions", expect_dict)
        with JsonParentContext("extensions"):
            operation_name = parse_expected_value(
                extensions, "operationName", expect_str
            )
        if expect_no_errors and errors is not None and len(errors) > 0:
            raise GQLResponseErrors(operation_name, errors)
        return errors or [], operation_name, data or {}

    def parse_video_player_stream_info_overlay_channel_data(self, response: Any):
        """
        Parses responses to VideoPlayerStreamInfoOverlayChannel requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return VideoPlayerStreamInfoOverlayChannelResponse(
                user=parse_expected_value(data, "user", user_parser),
            )

    def parse_get_id_from_login_response(self, response: Any):
        """
        Parses responses to GetIDFromLogin requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            user = parse_expected_value(data, "user", expect_dict)
            return GetIdFromLoginResponse(
                _id=parse_expected_value(user, "id", expect_str)
            )

    def parse_channel_follows_response(self, response: Any):
        """
        Parses responses to ChannelFollows requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            user = parse_expected_value(data, "user", expect_dict)
            with JsonParentContext("user"):
                # Ignore the user layer, we don't need it right now
                return ChannelFollowsResponse(
                    _id=parse_expected_value(user, "id", expect_str),
                    follows=parse_expected_value(
                        user, "follows", paginated_parser(follow_parser)
                    ),
                )

    def parse_join_raid_response(self, response: Any):
        """
        Parses responses to JoinRaid requests.
        :param response: The response to parse.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        self.parse_base_response(response, True)

    def parse_playback_access_token_response(self, response: Any):
        """
        Parses responses to PlaybackAccessToken requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            # Ignore streamPlaybackAccessToken, it's the only value in data
            stream_playback_access_token = parse_expected_value(
                data, "streamPlaybackAccessToken", expect_dict
            )
            with JsonParentContext("streamPlaybackAccessToken"):
                return PlaybackAccessTokenResponse(
                    value=parse_expected_value(
                        stream_playback_access_token, "value", expect_str
                    ),
                    signature=parse_expected_value(
                        stream_playback_access_token, "signature", expect_str
                    ),
                    authorization=parse_expected_value(
                        stream_playback_access_token,
                        "authorization",
                        authorization_parser,
                    ),
                )

    def parse_channel_points_context_response(self, response: Any):
        """
        Parses responses to ChannelPointsContext requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return ChannelPointsContextResponse(
                community=parse_expected_value(
                    data, "community", optional_parser(community_parser)
                ),
            )

    def parse_make_prediction_response(self, response: Any):
        """
        Parses responses to MakePrediction requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            make_prediction = parse_expected_value(data, "makePrediction", expect_dict)
            with JsonParentContext("makePrediction"):
                # Ignore makePrediction, it's the only value in data
                return Predictions.MakePredictionResponse(
                    error=parse_expected_value(
                        make_prediction,
                        "error",
                        optional_parser(prediction_error_parser),
                    ),
                )

    def parse_claim_community_points_response(self, response: Any):
        """
        Parses responses to ClaimCommunityPoints requests.
        :param response: The response to parse.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        self.parse_base_response(response, True)

    def parse_community_moment_callout_claim_response(self, response: Any):
        """
        Parses responses to CommunityMomentCalloutClaims requests.
        :param response: The response to parse.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        self.parse_base_response(response, True)

    def parse_drops_highlight_service_available_drops(self, response: Any):
        """
        Parses responses to DropsHighlightServiceAvailableDrops requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        # We're only interested in the ids
        with JsonParentContext("data"):
            channel = parse_expected_value(data, "channel", expect_dict)
            with JsonParentContext("channel"):
                viewer_drop_campaigns = parse_expected_value(
                    channel, "viewerDropCampaigns", optional_parser(expect_list)
                )
                ids = []
                if viewer_drop_campaigns is not None:
                    for index, campaign in enumerate(viewer_drop_campaigns):
                        with JsonParentContext(index):
                            ids.append(parse_expected_value(campaign, "id", expect_str))
                return DropsHighlightServiceAvailableDropsResponse(ids)

    def parse_inventory_response(self, response: Any):
        """
        Parses responses to Inventory requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        # We're only interested in the campaigns
        with JsonParentContext("data"):
            return dig(
                data,
                ["currentUser", "inventory"],
                lambda inventory: InventoryResponse(
                    parse_expected_value(
                        inventory,
                        "dropCampaignsInProgress",
                        optional_parser(list_parser(drop_campaign_in_progress_parser)),
                    )
                ),
            )

    def parse_viewer_drops_dashboard_response(self, response: Any):
        """
        Parses responses to ViewerDropsDashboard requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            current_user = parse_expected_value(data, "currentUser", expect_dict)
            with JsonParentContext("currentUser"):
                return Drops.ViewerDropsDashboardResponse(
                    campaigns=parse_expected_value(
                        current_user,
                        "dropCampaigns",
                        optional_parser(list_parser(drop_campaign_dashboard_parser)),
                    ),
                )

    def parse_drop_campaign_details_response(self, response: Any):
        """
        Parses responses to DropCampaignDetails requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        # We're only interested in the campaign
        with JsonParentContext("data"):
            user = parse_expected_value(data, "user", expect_dict)
            with JsonParentContext("user"):
                return Drops.DropCampaignDetailsResponse(
                    campaign=parse_expected_value(
                        user, "campaign", drop_campaign_details_parser
                    ),
                )

    def parse_drop_page_claim_drop_rewards(self, response: Any):
        """
        Parses responses to DropPage_ClaimDropRewards requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        status = None
        with JsonParentContext("data"):
            claim_drop_rewards = parse_expected_value(
                data, "claimDropRewards", optional_parser(expect_dict)
            )
            # Apparently this can be None but I couldn't find a case where it was
            if claim_drop_rewards is not None:
                with JsonParentContext("claimDropRewards"):
                    status = parse_expected_value(
                        claim_drop_rewards, "status", expect_str
                    )

            data_errors = parse_value(data, "errors", optional_parser(expect_list))
            return Drops.DropsPageClaimDropsResponse(status, data_errors)

    def parse_user_points_contribution(
        self, response: Any
    ) -> ChannelPointsContext.UserPointsContributionResponse:
        """
        Parses responses to UserPointsContribution requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return dig(
                data,
                ["user", "channel", "self", "communityPoints"],
                lambda community_points: ChannelPointsContext.UserPointsContributionResponse(
                    goal_contributions=parse_expected_value(
                        community_points,
                        "goalContributions",
                        list_parser(goal_contribution_parser),
                    ),
                ),
            )

    def parse_contribute_community_points_community_goal(
        self, response: Any
    ) -> ContributeToCommunityGoalResponse:
        """
        Parses responses to ContributeCommunityPointsCommunityGoal requests. Doesn't return anything, we're more
        interested in the errors.
        :param response: The response to parse.
        :raises: GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            contribute = parse_expected_value(
                data, "contributeCommunityPointsCommunityGoal", expect_dict
            )
            with JsonParentContext("contributeCommunityPointsCommunityGoal"):
                return ContributeToCommunityGoalResponse(
                    error=parse_expected_value(
                        contribute, "error", optional_parser(expect_str)
                    ),
                )

    def parse_with_is_stream_live_query(
        self, response: Any
    ) -> WithIsStreamLiveQueryResponse:
        """
        Parses responses to WithIsStreamLiveQuery requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return WithIsStreamLiveQueryResponse(
                user=parse_expected_value(
                    data, "user", with_is_stream_live_query_user_parser
                )
            )

    def parse_reward_list(self, response: Any) -> RewardListResponse:
        """
        Parses responses to RewardList requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return RewardList.RewardListResponse(
                channel=parse_expected_value(
                    data, "channel", reward_list_channel_parser
                ),
            )

    def parse_chat_room_ban_status(self, response: Any) -> ChatRoomBanStatusResponse:
        """
        Parses responses to ChatRoomBanStatus requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return ChatRoomBanStatusResponse(
                status=parse_expected_value(
                    data, "chatRoomBanStatus", optional_parser(expect_any)
                )
            )

    def parse_subscriptions_management_subscription_benefits(
        self, response
    ) -> SubscriptionManagement.SubscriptionBenefitResponse:
        """
        Parses responses to SubscriptionsManagement_SubscriptionBenefits requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises GQLError: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            user = parse_expected_value(data, "currentUser", expect_dict)
            with JsonParentContext("currentUser"):
                return SubscriptionManagement.SubscriptionBenefitResponse(
                    pages=parse_expected_value(
                        user,
                        "subscriptionBenefits",
                        paginated_parser(subscription_benefit_parser),
                    ),
                )

    def parse_weekly_rewards(self, response) -> WeeklyRewards.WeeklyRewards | None:
        """
        Parses responses to WeeklyVisitRewardsQuery requests.
        :param response: The response to parse.
        :return: The parsed response.
        :raises GQLResponseErrors: If the response contains errors or there is an issue parsing the response.
        """
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return dig(
                data,
                ["channel", "self", "weeklyVisitRewards"],
                optional_parser(weekly_visit_rewards_parser),
            )

    def parse_filterable_video_tower_videos(
        self, response
    ) -> FilterableVideoTower.Videos:
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return FilterableVideoTower.Videos(
                videos=dig(
                    data,
                    ["user", "videos"],
                    paginated_parser(filterable_video_tower_video_edge_parser),
                )
            )

    def parse_clips_cards_user(self, response) -> ClipsCardsUser.Response:
        _, _, data = self.parse_base_response(response, True)
        with JsonParentContext("data"):
            return ClipsCardsUser.Response(
                clips=dig(
                    data,
                    ["user", "clips"],
                    paginated_parser(clips_cards_user_clip_edge_parser),
                )
            )
