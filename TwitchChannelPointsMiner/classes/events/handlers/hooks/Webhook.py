from typing import Literal, TypedDict

import requests

from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.classes.events.handlers.hooks.Hook import (
    WebhookHandler,
    PostRequest,
)
from TwitchChannelPointsMiner.classes.events.transformers.Misc import MappingToDictTransformer
from TwitchChannelPointsMiner.classes.events.transformers.Strings import (
    DefaultStringTransformer,
)
from TwitchChannelPointsMiner.utils import AttemptStrategy
from TwitchChannelPointsMiner.utils.QueueRunner import QueueRunner


class WebhookData(TypedDict):
    message: str
    event_name: str


class WebhookTransformer(EventTransformer[WebhookData]):
    def __init__(self, get_message: EventTransformer[str] | None = None):
        self.get_message = (
            get_message if get_message is not None else DefaultStringTransformer()
        )

    def transform(self, event: Event) -> WebhookData:
        return {
            "message": self.get_message.transform(event),
            "event_name": (
                event.type.name if event.type.name is not None else type(event).__name__
            ),
        }


def webhook(
    webhook_api_url: str,
    name: str = "Webhook",
    method: Literal["post"] | Literal["get"] = "post",
    events: list[Events] | Events | None = None,
    use_json: bool = False,
    transformer: EventTransformer[WebhookData] | None = None,
    attempt_strategy: AttemptStrategy | None = None,
    timeout: float | tuple[float, float] | None = None,
):
    return GenericWebhook(
        name=name,
        webhook_api_url=webhook_api_url,
        method=method,
        use_json=use_json,
        events=events,
        transformer=(transformer if transformer is not None else WebhookTransformer()),
        attempt_strategy=attempt_strategy,
        timeout=timeout,
    )


class GenericWebhook(WebhookHandler):
    """Sends an Event via a generic webhook, supports post (with json and uri encoded data) and get requests"""

    def __init__(
        self,
        name: str,
        webhook_api_url: str,
        transformer: EventTransformer[WebhookData],
        method: Literal["post"] | Literal["get"] = "post",
        events: list[Events] | Events | None = None,
        use_json: bool = False,
        attempt_strategy: AttemptStrategy | None = None,
        timeout: float | tuple[float, float] | None = None,
        post_request: PostRequest | None = None,
        runner: QueueRunner | None = None,
    ):
        if webhook_api_url == "https://example.com/webhook":
            raise ValueError(
                f"URL ({webhook_api_url}) is from the example, please use your own"
            )
        super().__init__(
            name=name,
            webhook_api_url=webhook_api_url,
            events=events,
            use_json=use_json,
            # This is fine as TypedDict can be used in place of dict
            transformer=MappingToDictTransformer(base=transformer),
            attempt_strategy=attempt_strategy,
            timeout=timeout,
            post_request=post_request,
            runner=runner,
        )
        self.method = method

    def _make_request(self, data: dict):
        if self.method == "post":
            return super()._make_request(data)
        else:
            url_with_params = f"{self.webhook_api_url}?event_name={data["event_name"]}&message={data["message"]}"
            return requests.get(url=url_with_params, timeout=self.timeout)
