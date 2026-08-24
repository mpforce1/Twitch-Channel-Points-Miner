import requests

from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.classes.events.handlers.Factory import EventHandlerFactory
from TwitchChannelPointsMiner.classes.events.handlers.hooks.Hook import WebhookHandler
from TwitchChannelPointsMiner.utils import AttemptStrategy


class MatrixTransformer(EventTransformer[dict]):
    def __init__(self, get_body: EventTransformer[str]):
        self.get_body = get_body

    def transform(self, event: Event) -> dict:
        return {
            "body": self.get_body.transform(event),
            "msgtype": "m.text",
        }


def matrix(
    username: str,
    password: str,
    homeserver: str,
    room_id: str,
    name: str = "Matrix",
    events: list[Events] | Events | None = None,
    transformer: EventTransformer[dict] | None = None,
    get_body: EventTransformer[str] | None = None,
    attempt_strategy: AttemptStrategy | None = None,
    timeout: float | tuple[float, float] | None = None,
) -> EventHandlerFactory:
    body = requests.post(
        url=f"https://{homeserver}/_matrix/client/r0/login",
        json={"user": username, "password": password, "type": "m.login.password"},
    ).json()

    access_token = body.get("access_token")

    if not access_token:
        raise ValueError(
            "Invalid Matrix password provided. Please check your configuration."
        )

    webhook_api_url = f"https://{homeserver}/_matrix/client/r0/rooms/{room_id}/send/m.room.message?access_token={access_token}"

    def factory(logger_settings, background_tasks, default_transformer, account_name):
        handler = WebhookHandler(
            name=name,
            webhook_api_url=webhook_api_url,
            events=events,
            transformer=(
                transformer
                if transformer is not None
                else MatrixTransformer(
                    get_body=get_body if get_body is not None else default_transformer
                )
            ),
            attempt_strategy=attempt_strategy,
            timeout=timeout,
        )
        background_tasks.append(handler.runner)
        return handler

    return factory
