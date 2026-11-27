import abc
import copy
from dataclasses import dataclass
from secrets import token_hex
from typing import Literal, Tuple

from TwitchChannelPointsMiner.classes.Settings import Settings


@dataclass
class GQLQuery:
    """A Query for the Twitch GQL endpoint, includes some members useful for logging and the data payload."""

    name: str
    """A useful name that describes this query"""
    data: dict
    """The data payload that can be serialised and sent to Twitch"""
    redacted_data: dict
    """The data payload with redactions for logging"""


class PersistedQuery(abc.ABC):
    """A GQL Persisted Query builder, without the data payload"""

    name: str
    """The Operation name of the query"""
    sha256_hash: str
    """The SHA256 hash of the query"""

    def to_dict(self):
        """Creates the base data payload for this Query"""
        base = {
            "operationName": self.name,
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": self.sha256_hash,
                }
            },
        }

        return base

    def with_variables(self, variables: dict | None = None) -> GQLQuery:
        """
        Creates a GQLQuery with a payload with an optional 'variables' value.
        :param variables: The optional variables to add to the payload.
        """
        data = self.to_dict()
        if variables is not None:
            data["variables"] = variables
        return GQLQuery(
            name=self.name,
            data=data,
            redacted_data=self.redact(data),
        )

    def redact(self, data: dict):
        """
        Creates a redacted copy of the data for use when logging anonymously or with redacted secrets.
        :param data: The data to redact.
        :return: The redacted data.
        """
        return copy.deepcopy(data)


# Redaction helper functions


def set_value(data: dict, key_path: list[str], value):
    """
    Set a value in a dict using the given list of strings as a json path.
    :param data: The data dict.
    :param key_path: The json path of the value to set.
    :param value: The value to set.
    """
    if len(key_path) == 0:
        return
    if len(key_path) == 1:
        data[key_path[0]] = value
        return
    set_value(data[key_path[0]], key_path[1:], value)


def get_value(data: dict, key_path: list[str]):
    """
    Get a value in a dict using the given list of strings as a json path.
    :param data: The data dict.
    :param key_path: The json path of the value to get.
    :return: The value found.
    """
    if len(key_path) == 0:
        return data
    if len(key_path) == 1:
        return data[key_path[0]]
    return get_value(data[key_path[0]], key_path[1:])


def redact(
    data: dict, *redactions: Tuple[list[str], Literal["channel id", "username"]]
):
    """
    Redacts a list of values in a data dict. A redaction is a tuple of path and redation type, i.e:

    `(["path1", "path2"], "channel id")`
    =>
    `dict["path1"]["path2"] =  Settings.logger.anonymiser.channel_id(dict["path1"]["path2"])`

    :param data: The data dict.
    :param redactions: The list of redactions to make.
    :return:
    """
    data = copy.deepcopy(data)
    for key_path, redaction_type in redactions:
        value = get_value(data["variables"], key_path)
        match redaction_type:
            case "channel id":
                new_value = Settings.logger.anonymiser.channel_id(value)
            case "username":
                new_value = Settings.logger.anonymiser.username(value)
            case _:
                raise ValueError(f"Unknown redaction_type: {redaction_type}")
        set_value(data["variables"], key_path, new_value)
    return data


# Operations


@dataclass
class WithStreamIsLive(PersistedQuery):
    name = "WithIsStreamLiveQuery"
    sha256_hash = "04e46329a6786ff3a81c01c50bfa5d725902507a0deb83b0edbf7abe7a3716ea"

    def prepare(self, _id: str):
        return self.with_variables({"id": _id})

    def redact(self, data: dict):
        return redact(data, (["id"], "channel id"))


@dataclass
class PlaybackAccessToken(PersistedQuery):
    name = "PlaybackAccessToken"
    sha256_hash = "ed230aa1e33e07eebb8928504583da78a5173989fadfb1ac94be06a04f3cdbe9"

    def prepare(
        self,
        login: str,
        is_live: bool = True,
        is_vod: bool = False,
        vod_id: str = "",
        player_type: str = "site",
        platform: str = "web",
    ):
        return self.with_variables(
            {
                "login": login,
                "isLive": is_live,
                "isVod": is_vod,
                "vodID": vod_id,
                "playerType": player_type,
                "platform": platform,
            }
        )

    def redact(self, data: dict):
        return redact(data, (["login"], "username"))


class VideoPlayerStreamInfoOverlayChannel(PersistedQuery):
    name = "VideoPlayerStreamInfoOverlayChannel"
    sha256_hash = "e785b65ff71ad7b363b34878335f27dd9372869ad0c5740a130b9268bcdbe7e7"

    def prepare(self, channel: str):
        return self.with_variables({"channel": channel})

    def redact(self, data: dict):
        return redact(data, (["channel"], "username"))


class ClaimCommunityPoints(PersistedQuery):
    name = "ClaimCommunityPoints"
    sha256_hash = "46aaeebe02c99afdf4fc97c7c0cba964124bf6b0af229395f1f6d1feed05b3d0"

    def prepare(self, channel_id: str, claim_id: str):
        return self.with_variables(
            {"input": {"channelID": channel_id, "claimID": claim_id}}
        )

    def redact(self, data: dict):
        return redact(data, (["input", "channelID"], "channel id"))


class CommunityMomentCalloutClaim(PersistedQuery):
    name = "CommunityMomentCallout_Claim"
    sha256_hash = "e2d67415aead910f7f9ceb45a77b750a1e1d9622c936d832328a0689e054db62"

    def prepare(self, moment_id: str):
        return self.with_variables({"input": {"momentID": moment_id}})


@dataclass
class DropsPageClaimDropRewards(PersistedQuery):
    name = "DropsPage_ClaimDropRewards"
    sha256_hash = "3b8a08f5a35dc95d7de229dea731a106a9aa9fa2e84c8f693fd159943f273e4f"

    def prepare(self, drop_instance_id: str):
        return self.with_variables({"input": {"dropInstanceID": drop_instance_id}})


@dataclass
class ChannelPointsContext(PersistedQuery):
    name = "ChannelPointsContext"
    sha256_hash = "7fe050e3761eb2cf258d70ee1a21cbd76fa8cf3d7e7b12fc437e7029d446b5e3"

    def prepare(self, channel_login: str):
        return self.with_variables({"channelLogin": channel_login})

    def redact(self, data: dict):
        return redact(data, (["channelLogin"], "username"))


@dataclass
class JoinRaid(PersistedQuery):
    name = "JoinRaid"
    sha256_hash = "c6a332a86d1087fbbb1a8623aa01bd1313d2386e7c63be60fdb2d1901f01a4ae"

    def prepare(self, raid_id: str):
        return self.with_variables({"input": {"raidID": raid_id}})


@dataclass
class Inventory(PersistedQuery):
    name = "Inventory"
    sha256_hash = "3ab317a5753b25125f47d4ce962ebe928ff4e85047b77508340c94ebc20b6230"

    def prepare(self, fetch_reward_campaigns: bool = True):
        return self.with_variables({"fetchRewardCampaigns": fetch_reward_campaigns})


@dataclass
class MakePrediction(PersistedQuery):
    name = "MakePrediction"
    sha256_hash = "b44682ecc88358817009f20e69d75081b1e58825bb40aa53d5dbadcc17c881d8"

    def prepare(
        self,
        event_id: str,
        outcome_id: str,
        points: int,
        transaction_id: str | None = None,
    ):
        return self.with_variables(
            {
                "input": {
                    "eventID": event_id,
                    "outcomeID": outcome_id,
                    "points": points,
                    "transactionID": (
                        transaction_id if transaction_id is not None else token_hex(16)
                    ),
                }
            }
        )


@dataclass
class ViewerDropsDashboard(PersistedQuery):
    name = "ViewerDropsDashboard"
    sha256_hash = "d9cae7761dafab85908c85e6683cb4201b449e66ac3bb5e894f15ff12aeafaa7"

    def prepare(self, fetch_reward_campaigns: bool = True):
        return self.with_variables({"fetchRewardCampaigns": fetch_reward_campaigns})


@dataclass
class DropCampaignDetails(PersistedQuery):
    name = "DropCampaignDetails"
    sha256_hash = "039277bf98f3130929262cc7c6efd9c141ca3749cb6dca442fc8ead9a53f77c1"

    def prepare(self, drop_id: str, user_id: int):
        return self.with_variables(
            {
                "dropID": drop_id,
                "channelLogin": f"{user_id}",
            }
        )

    def redact(self, data: dict):
        return redact(data, (["channelLogin"], "username"))


@dataclass
class DropsHighlightServiceAvailableDrops(PersistedQuery):
    name = "DropsHighlightService_AvailableDrops"
    sha256_hash = "782dad0f032942260171d2d80a654f88bdd0c5a9dddc392e9bc92218a0f42d20"

    def prepare(self, channel_id: str):
        return self.with_variables({"channelID": channel_id})

    def redact(self, data: dict):
        return redact(data, (["channelID"], "channel id"))


@dataclass
class GetIDFromLogin(PersistedQuery):
    name = "GetIDFromLogin"
    sha256_hash = "94e82a7b1e3c21e186daa73ee2afc4b8f23bade1fbbff6fe8ac133f50a2f58ca"

    def prepare(self, login: str):
        return self.with_variables({"login": login})

    def redact(self, data: dict):
        return redact(data, (["login"], "username"))


@dataclass
class ChannelFollows(PersistedQuery):
    name = "ChannelFollows"
    sha256_hash = "eecf815273d3d949e5cf0085cc5084cd8a1b5b7b6f7990cf43cb0beadf546907"

    def prepare(self, limit: int = 100, order: str = "ASC", cursor: str = ""):
        return self.with_variables({"limit": limit, "order": order, "cursor": cursor})


@dataclass
class UserPointsContribution(PersistedQuery):
    name = "UserPointsContribution"
    sha256_hash = "23ff2c2d60708379131178742327ead913b93b1bd6f665517a6d9085b73f661f"

    def prepare(self, username: str):
        return self.with_variables({"channelLogin": username})

    def redact(self, data: dict):
        return redact(data, (["channelLogin"], "username"))


@dataclass
class ContributeCommunityPointsCommunityGoal(PersistedQuery):
    name = "ContributeCommunityPointsCommunityGoal"
    sha256_hash = "5774f0ea5d89587d73021a2e03c3c44777d903840c608754a1be519f51e37bb6"

    def prepare(
        self,
        amount: int,
        channel_id: str,
        goal_id: str,
        transaction_id: str | None = None,
    ):
        return self.with_variables(
            {
                "input": {
                    "amount": amount,
                    "channelID": channel_id,
                    "goalID": goal_id,
                    "transactionID": (
                        transaction_id if transaction_id is not None else token_hex(16)
                    ),
                }
            }
        )

    def redact(self, data: dict):
        return redact(data, (["input", "channelID"], "channel id"))


@dataclass
class RewardList(PersistedQuery):
    name = "RewardList"
    sha256_hash = "0b1471876d7647993731b9e3c6a13bf304c67fb31d07f06a945d42286ee377c4"

    def prepare(
        self, channel_id: str, should_include_all_suspended_streaks: bool = False
    ):
        return self.with_variables(
            {
                "shouldIncludeAllSuspendedStreaks": should_include_all_suspended_streaks,
                "channelID": channel_id,
            }
        )

    def redact(self, data: dict):
        return redact(data, (["channelID"], "channel id"))


@dataclass
class ChatRoomBanStatus(PersistedQuery):
    name = "ChatRoomBanStatus"
    sha256_hash = "319f2a9a3ac7ddecd7925944416c14b818b65676ab69da604460b68938d22bea"

    def prepare(self, user_id: int, channel_id: str):
        return self.with_variables(
            {"targetUserID": f"{user_id}", "channelID": channel_id}
        )

    def redact(self, data: dict):
        return redact(
            data, (["targetUserID"], "channel id"), (["channelID"], "channel id")
        )


@dataclass
class SubscriptionsManagementSubscriptionBenefits(PersistedQuery):
    name = "SubscriptionsManagement_SubscriptionBenefits"
    sha256_hash = "dfac9fc0965996a636f07fd98ae5f9878a628134b330b47a0d26c02a0c225854"

    def prepare(
        self,
        cursor: str,
        _filter: str = "GIFT",
        limit: int = 100,
        platform: str = "WEB",
    ):
        return self.with_variables(
            {"cursor": cursor, "filter": _filter, "limit": limit, "platform": platform}
        )


@dataclass
class WeeklyVisitRewardsQuery(PersistedQuery):
    name = "WeeklyVisitRewardsQuery"
    sha256_hash = "ce98e9db55db7e4abcc1f5ac65c933b73c58fa9c4c8afe3c5098a8ed79737a3c"

    def prepare(self, channel_id: str):
        return self.with_variables({"channelID": channel_id})

    def redact(self, data: dict):
        return redact(data, (["channelID"], "channel id"))


@dataclass
class FilterableVideoTowerVideos(PersistedQuery):
    name = "FilterableVideoTower_Videos"
    sha256_hash = "67004f7881e65c297936f32c75246470629557a393788fb5a69d6d9a25a8fd5f"

    def prepare(
        self,
        channel_owner_login: str,
        limit: int,
        broadcast_type: str = "ARCHIVE",
        include_preview_blur: bool = False,
        video_sort: str = "TIME",
    ):
        return self.with_variables(
            {
                "broadcastType": broadcast_type,
                "includePreviewBlur": include_preview_blur,
                "videoSort": video_sort,
                "channelOwnerLogin": channel_owner_login,
                "limit": limit,
            }
        )

    def redact(self, data: dict):
        return redact(data, (["channelOwnerLogin"], "username"))


@dataclass
class ClipsCardsUser(PersistedQuery):
    name = "ClipsCards__User"
    sha256_hash = "1cd671bfa12cec480499c087319f26d21925e9695d1f80225aae6a4354f23088"

    def prepare(self, login: str, limit: int, _filter: str):
        return self.with_variables(
            {"login": login, "limit": limit, "criteria": {"filter": _filter}}
        )

    def redact(self, data: dict):
        return redact(data, (["login"], "username"))


@dataclass
class DropChannelCampaignsProgress(PersistedQuery):
    name = "DropChannelCampaignsProgress"
    sha256_hash = "3d9ce923899cbab5d7a8481da4e9918b1982a987bac68ac4347b5cf925a1d523"

    def prepare(self, channel_id: str):
        return self.with_variables({"channelID": channel_id})

    def redact(self, data: dict):
        return redact(data, (["channelID"], "channel id"))


@dataclass
class ViewerRewardDropInventory(PersistedQuery):
    name = "ViewerRewardDropInventory"
    sha256_hash = "828f9f0bdbc735ce3162519717f918b811902984580389a67ad733c684291e62"

    def prepare(self):
        return self.with_variables()


@dataclass
class Operations:
    with_is_stream_live = WithStreamIsLive()
    playback_access_token = PlaybackAccessToken()
    video_player_stream_info_overlay_channel = VideoPlayerStreamInfoOverlayChannel()
    claim_community_points = ClaimCommunityPoints()
    community_moment_callout_claim = CommunityMomentCalloutClaim()
    drops_page_claim_drop_rewards = DropsPageClaimDropRewards()
    channel_points_context = ChannelPointsContext()
    join_raid = JoinRaid()
    inventory = Inventory()
    make_prediction = MakePrediction()
    viewer_drops_dashboard = ViewerDropsDashboard()
    drop_campaign_details = DropCampaignDetails()
    drops_highlight_service_available_drops = DropsHighlightServiceAvailableDrops()
    get_id_from_login = GetIDFromLogin()
    channel_follows = ChannelFollows()
    user_points_contribution = UserPointsContribution()
    contribute_community_points_community_goal = (
        ContributeCommunityPointsCommunityGoal()
    )
    reward_list = RewardList()
    chat_room_ban_status = ChatRoomBanStatus()
    subscriptions_management_subscription_benefits = (
        SubscriptionsManagementSubscriptionBenefits()
    )
    weekly_visit_rewards_query = WeeklyVisitRewardsQuery()
    filterable_video_tower_videos = FilterableVideoTowerVideos()
    clips_cards_user = ClipsCardsUser()
    drop_channel_campaigns_progress = DropChannelCampaignsProgress()
    viewer_reward_drop_inventory = ViewerRewardDropInventory()


# Operations Singleton
operations = Operations()
