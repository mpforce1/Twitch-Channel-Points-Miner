from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.classes.events.handlers.Factory import EventHandlerFactory
from TwitchChannelPointsMiner.classes.events.handlers.hooks.Hook import (
    WebhookHandler,
)
from TwitchChannelPointsMiner.utils import AttemptStrategy


class PushoverTransformer(EventTransformer[dict]):
    def __init__(
        self,
        userkey: str,
        token: str,
        priority,
        sound,
        title: str | None,
        get_message: EventTransformer[str],
    ):
        self.userkey = userkey
        self.token = token
        self.priority = priority
        self.sound = sound
        self.title = title if title is not None else "Twitch Channel Points Miner"
        self.get_message = get_message

    def transform(self, event: Event) -> dict:
        return {
            "user": self.userkey,
            "token": self.token,
            "message": self.get_message.transform(event),
            "title": self.title,
            "priority": self.priority,
            "sound": self.sound,
        }


def pushover(
    userkey: str,
    token: str,
    priority,
    sound,
    title: str | None,
    webhook_api_url: str,
    name: str = "Pushover",
    events: list[Events] | Events | None = None,
    transformer: EventTransformer[dict] | None = None,
    get_message: EventTransformer[str] | None = None,
    attempt_strategy: AttemptStrategy | None = None,
    timeout: float | tuple[float, float] | None = None,
) -> EventHandlerFactory:
    if userkey == "YOUR-ACCOUNT-TOKEN":
        raise ValueError(
            f"userkey '{userkey}' is from the example, please provide your own"
        )
    if token == "YOUR-APPLICATION-TOKEN":
        raise ValueError(
            f"token '{token} is from the example, please provide your own'"
        )
    return lambda default_transformer: WebhookHandler(
        name=name,
        webhook_api_url=webhook_api_url,
        events=events,
        transformer=(
            transformer
            if transformer is not None
            else PushoverTransformer(
                userkey=userkey,
                token=token,
                priority=priority,
                sound=sound,
                title=title,
                get_message=(
                    get_message if get_message is not None else default_transformer
                ),
            )
        ),
        attempt_strategy=attempt_strategy,
        timeout=timeout,
    )
