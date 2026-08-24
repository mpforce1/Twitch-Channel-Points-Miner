import datetime
from typing import NotRequired, TypedDict

from TwitchChannelPointsMiner.classes.Translator import Translator
from TwitchChannelPointsMiner.classes.entities.predictions.Outcome import Outcome
from TwitchChannelPointsMiner.classes.entities.predictions.Prediction import Prediction
from TwitchChannelPointsMiner.classes.events.Event import (
    ChannelEvent,
    Event,
    GiftSubReceived,
    PredictionEventCreated,
    PredictionEventEvent,
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
        translator: Translator,
        account_name: str,
        username: str | None = "Twitch Channel Points Miner",
        avatar_url: str | None = "https://i.imgur.com/X9fEkhT.png",
        locale: str | None = None,
    ):
        self.translator = translator
        self.account_name = account_name
        self.username = username
        self.avatar_url = avatar_url
        self.locale = locale

    def event_name(self, event: Event):
        return self.translator.translate_str(lambda t: t.names[event.type], self.locale)

    def account_field(self) -> Field:
        return {
            "name": f"👤 {self.translator.translate_str(lambda t: t.general.account, self.locale)}",
            "value": self.account_name,
        }

    def channel_field(self, event: ChannelEvent) -> Field:
        return {
            "name": f"📺 {self.translator.translate_str(lambda t: t.general.channel, self.locale)}",
            "value": event.streamer.username,
        }

    def title_field(self, event: PredictionEventEvent) -> Field:
        return {
            "name": f"🎯 {self.translator.translate_str(lambda t: t.general.title, self.locale)}",
            "value": event.prediction_event.title,
        }

    def outcome_field(self, index: int, outcome: Outcome) -> Field:
        return {
            "name": f"{index_to_emoji(index)}",
            "value": outcome.title,
            "inline": True,
        }

    def your_prediction_field(self, prediction: Prediction, outcome: Outcome) -> Field:
        return {
            "name": f"🔮 {self.translator.translate_str(lambda t: t.predictions.your_prediction, self.locale)}",
            "value": self.translator.translate(
                lambda t: t.predictions.prediction_multiline,
                arg={
                    "title": outcome.title,
                    "odds": outcome.odds,
                    "points": prediction.points,
                },
            ),
        }

    def prediction_event_created(self, event: PredictionEventCreated) -> Embed:
        fields: list[Field] = [
            self.account_field(),
            self.channel_field(event),
            self.title_field(event),
            {
                "name": f"🪟 {self.translator.translate_str(lambda t: t.general.window, self.locale)}",
                "value": f"{event.prediction_event.prediction_window_seconds}s",
                "inline": True,
            },
            {
                "name": f"🎫 {self.translator.translate_str(lambda t: t.general.outcomes, self.locale)}:",
                "value": "\n",
            },
        ]
        fields.extend(
            [
                self.outcome_field(index, outcome)
                for index, outcome in enumerate(event.prediction_event.outcomes)
            ]
        )
        return {
            "color": 16711680,
            "title": f"🍀 {self.event_name(event)}",
            "fields": fields,
        }

    def prediction_made(self, event: PredictionMade) -> Embed:
        user_prediction = event.prediction
        user_outcome = event.prediction_event.outcome(user_prediction.outcome_id)
        return {
            "color": 654321,
            "title": f"🍀 {self.event_name(event)}",
            "fields": [
                self.account_field(),
                self.channel_field(event),
                self.title_field(event),
                self.your_prediction_field(user_prediction, user_outcome),
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
            self.account_field(),
            self.channel_field(event),
            self.title_field(event),
        ]
        if winning_outcome is not None:
            fields.append(
                {
                    "name": f"🏆 {self.translator.translate_str(lambda t: t.predictions.winning_outcome, self.locale)}",
                    "value": self.translator.translate(
                        lambda t: t.predictions.outcome_multiline,
                        arg={
                            "title": winning_outcome.title,
                            "odds": winning_outcome.odds,
                        },
                        locale=self.locale,
                    ),
                    "inline": True,
                }
            )
        fields.extend(
            [
                self.your_prediction_field(user_prediction, user_outcome),
                {
                    "name": f"📩 {self.translator.translate_str(lambda t: t.predictions.result, self.locale)}",
                    "value": user_result.type,
                },
                {
                    "name": f"📊 {self.translator.translate_str(lambda t: t.predictions.profit_loss, self.locale)}",
                    "value": f"{net}",
                },
            ]
        )

        return {
            "color": 16711680,
            "title": f"🍀 {self.event_name(event)}",
            "fields": fields,
        }

    def gift_sub_received(self, event: GiftSubReceived) -> Embed:
        gift_sub = event.streamer.gift_sub
        if gift_sub is None:
            raise ValueError("Gift sib received event but there's no gift sub")
        gifter = self.translator.translate_optional(
            lambda t: t.gift_sub_received.gifter,
            gift_sub.gifter,
            lambda g: {"value": g.display_name},
            locale=self.locale,
        )
        if isinstance(gift_sub.tier, int):
            sub_name = self.translator.translate(
                lambda t: t.gift_sub_received.tier,
                arg={"tier": gift_sub.tier},
                locale=self.locale,
            )
        else:
            sub_name = gift_sub.tier
        ends_at = gift_sub.ends_at.astimezone(datetime.datetime.now().tzinfo)
        days = (gift_sub.ends_at - datetime.datetime.now(tz=datetime.timezone.utc)).days
        return {
            "color": 7798955,
            "title": f"🎁 {self.event_name(event)}",
            "fields": [
                self.account_field(),
                {
                    "name": f"🎅 {self.translator.translate_str(lambda t: t.gift_sub_received.from_, self.locale)}",
                    "value": gifter,
                    "inline": True,
                },
                {
                    "name": f"👑 {self.translator.translate_str(lambda t: t.gift_sub_received.subscription, self.locale)}",
                    "value": sub_name,
                },
                {
                    "name": f"📅 {self.translator.translate_str(lambda t: t.gift_sub_received.ends_at, self.locale)}",
                    "value": f"{ends_at}",
                    "inline": True,
                },
                {
                    "name": f"🕒 {self.translator.translate_str(lambda t: t.gift_sub_received.duration, self.locale)}",
                    "value": self.translator.translate_plural(
                        lambda t: t.gift_sub_received.days,
                        arg={"count": days},
                        locale=self.locale,
                    ),
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
