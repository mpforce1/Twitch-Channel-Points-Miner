import datetime
from typing import NotRequired, TypedDict

from TwitchChannelPointsMiner.classes.events.Event import (
    Event,
    GiftSubReceived,
    PredictionEventCreated,
    PredictionMade,
    PredictionResult,
)
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer


class DiscordContentTransformer(EventTransformer[dict]):
    """Transformer that produces post data compatible with Discord's Incoming Webhook API"""

    def __init__(
        self,
        get_content: EventTransformer[str],
        username: str | None = "Twitch Channel Points Miner",
        avatar_url: str | None = "https://i.imgur.com/X9fEkhT.png",
    ) -> None:
        self.username = username
        self.avatar_url = avatar_url
        self.get_content = get_content

    def transform(self, event: Event) -> dict[str, str]:
        data = {"content": self.get_content.transform(event)}
        if self.username is not None:
            data["username"] = self.username
        if self.avatar_url is not None:
            data["avatar_url"] = self.avatar_url
        return data


class Field(TypedDict):
    name: str
    """The field name, effectively a title"""
    value: str
    """The field value, the body"""
    inline: NotRequired[bool]
    """Whether the field renders inline, defaults to False"""


class Embed(TypedDict):
    color: int
    """The color of the (edge of the) message"""
    title: str
    """The message title"""
    description: NotRequired[str]
    """The message description, main body"""
    fields: list[Field]
    """A list of Field objects"""


def index_to_emoji(index: int) -> str:
    if 0 <= index <= 10:
        return ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][
            index
        ]
    else:
        return f"{index}"


class DiscordEmbedTransformer(EventTransformer[dict | None]):
    def __init__(
        self,
        account_name: str,
        username: str | None = "Twitch Channel Points Miner",
        avatar_url: str | None = "https://i.imgur.com/X9fEkhT.png",
    ):
        self.account_name = account_name
        self.username = username
        self.avatar_url = avatar_url

    def prediction_event_created(self, event: PredictionEventCreated) -> Embed:
        fields: list[Field] = [
            {
                "name": "👤 Account",
                "value": self.account_name,
            },
            {
                "name": "📺 Channel",
                "value": event.streamer.username,
            },
            {
                "name": "🎯 Title",
                "value": event.prediction_event.title,
                "inline": True,
            },
            {
                "name": "🪟 Window",
                "value": f"{event.prediction_event.prediction_window_seconds}s",
                "inline": True,
            },
            {
                "name": "🎫 Outcomes:",
                "value": "\n",
            },
        ]
        fields.extend(
            [
                {
                    "name": f"{index_to_emoji(index)}",
                    "value": outcome.title,
                    "inline": True,
                }
                for index, outcome in enumerate(event.prediction_event.outcomes)
            ]
        )
        return {
            "color": 16711680,
            "title": "🍀 Prediction Event Started",
            "fields": fields,
        }

    def prediction_made(self, event: PredictionMade) -> Embed:
        # 🍀  Prediction made for lacy (13.79k points) on 'Does he win?' - 725 points on 'Yes'
        user_prediction = event.prediction
        user_outcome = event.prediction_event.outcome(user_prediction.outcome_id)
        return {
            "color": 654321,
            "title": "🍀 Prediction Made",
            "fields": [
                {
                    "name": "👤 Account",
                    "value": self.account_name,
                },
                {
                    "name": "📺 Channel",
                    "value": event.streamer.username,
                },
                {
                    "name": "🎯 Title",
                    "value": event.prediction_event.title,
                },
                {
                    "name": "🔮 Your Prediction",
                    "value": f"{user_outcome.title}\n"
                    f"`Odds: {user_outcome.odds}`\n"
                    f"`Points Placed: {user_prediction.points}`",
                },
            ],
        }

    def prediction_result(self, event: PredictionResult) -> Embed:
        user_prediction = event.prediction_event.prediction
        if user_prediction is None:
            raise ValueError(f"Prediction result event has no prediction")
        user_outcome = event.prediction_event.outcome(user_prediction.outcome_id)
        user_result = user_prediction.result
        if user_result is None:
            raise ValueError(f"Prediction result event has no user result")
        if user_result.type == "WIN":
            if user_result.points_won is None:
                raise ValueError(f"Prediction WIN Result doesn't contain points won")
            net = user_result.points_won - user_prediction.points
        elif user_result.type == "LOSE":
            net = -user_prediction.points
        else:
            net = 0
        winning_outcome = event.prediction_event.winning_outcome()
        fields: list[Field] = [
            {
                "name": "👤 Account",
                "value": self.account_name,
            },
            {
                "name": "📺 Channel",
                "value": event.streamer.username,
            },
            {
                "name": "🎯 Title",
                "value": event.prediction_event.title,
            },
        ]
        if winning_outcome is not None:
            fields.append(
                {
                    "name": "🏆 Winning Outcome",
                    "value": f"{winning_outcome.title}\n"
                    f"`Odds: {winning_outcome.odds}`\n",
                    "inline": True,
                }
            )
        fields.extend(
            [
                {
                    "name": "🔮 Your Prediction",
                    "value": f"{user_outcome.title}\n"
                    f"`Odds: {user_outcome.odds}`\n"
                    f"`Points Placed: {user_prediction.points}`",
                    "inline": True,
                },
                {
                    "name": "📩 Result",
                    "value": user_result.type,
                },
                {
                    "name": "📊 Profit/Loss",
                    "value": f"{net}",
                },
            ]
        )

        return {
            "color": 16711680,
            "title": "🍀 Prediction Result",
            "fields": fields,
        }

    def gift_sub_received(self, event: GiftSubReceived) -> Embed:
        gift_sub = event.streamer.gift_sub
        if gift_sub is None:
            raise ValueError("Gift sib received event but there's no gift sub")
        gifter = (
            gift_sub.gifter.display_name if gift_sub.gifter is not None else "Anonymous"
        )
        sub_name = (
            f"Tier-{gift_sub.tier}" if isinstance(gift_sub.tier, int) else gift_sub.tier
        )
        ends_at = gift_sub.ends_at.astimezone(datetime.datetime.now().tzinfo)
        days = (gift_sub.ends_at - datetime.datetime.now(tz=datetime.timezone.utc)).days
        return {
            "color": 7798955,
            "title": "🎁 Gift Sub Received",
            "fields": [
                {
                    "name": "👤 Account",
                    "value": self.account_name,
                    "inline": True,
                },
                {
                    "name": "🎅 From",
                    "value": gifter,
                    "inline": True,
                },
                {
                    "name": "👑 Subscription",
                    "value": sub_name,
                },
                {
                    "name": "📅 Ends At",
                    "value": f"{ends_at}",
                    "inline": True,
                },
                {
                    "name": "🕒 Duration",
                    "value": f"{days} Days",
                    "inline": True,
                },
            ],
        }

    def transform(self, event: Event) -> dict | None:
        embedded = None
        match event:
            case PredictionEventCreated():
                embedded = self.prediction_event_created(event)
            case PredictionMade():
                embedded = self.prediction_made(event)
            case PredictionResult():
                embedded = self.prediction_result(event)
            case GiftSubReceived():
                embedded = self.gift_sub_received(event)
            case _:
                embedded = None
        if embedded is not None:
            data: dict = {"embeds": [embedded]}
            if self.username is not None:
                data["username"] = self.username
            if self.avatar_url is not None:
                data["avatar_url"] = self.avatar_url
            return data
        else:
            return None


class DiscordEitherTransformer(EventTransformer[dict]):
    def __init__(self, base: DiscordContentTransformer, embed: DiscordEmbedTransformer):
        self.base = base
        self.embed = embed

    def transform(self, event: Event) -> dict:
        embedded = self.embed.transform(event)
        if embedded is not None:
            return embedded
        else:
            return self.base.transform(event)
