from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.classes.events.handlers.Factory import EventHandlerFactory
from TwitchChannelPointsMiner.classes.events.handlers.hooks.Hook import (
    WebhookHandler,
)
from TwitchChannelPointsMiner.utils import AttemptStrategy


class GotifyTransformer(EventTransformer[dict]):
    def __init__(self, priority: int, get_message: EventTransformer[str]):
        self.priority = priority
        self.get_message = get_message

    def transform(self, event: Event) -> dict:
        return {"message": self.get_message.transform(event), "priority": self.priority}


def gotify(
    webhook_api_url: str,
    priority: int,
    name: str = "Gotify",
    events: list[Events] | Events | None = None,
    transformer: EventTransformer[dict] | None = None,
    get_message: EventTransformer[str] | None = None,
    attempt_strategy: AttemptStrategy | None = None,
    timeout: float | tuple[float, float] | None = None,
) -> EventHandlerFactory:
    if webhook_api_url == "https://example.com/message?token=TOKEN":
        raise ValueError(
            f"URL ({webhook_api_url}) is from the example, please use your own"
        )

    def factory(logger_settings, background_tasks, default_transformer, account_name):
        handler = WebhookHandler(
            name=name,
            webhook_api_url=webhook_api_url,
            events=events,
            transformer=(
                transformer
                if transformer is not None
                else GotifyTransformer(
                    priority=priority,
                    get_message=(
                        get_message if get_message is not None else default_transformer
                    ),
                )
            ),
            attempt_strategy=attempt_strategy,
            timeout=timeout,
        )
        background_tasks.append(handler.runner)
        return handler

    return factory
