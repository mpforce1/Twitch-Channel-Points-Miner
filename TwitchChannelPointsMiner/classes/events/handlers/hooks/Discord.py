from urllib.parse import parse_qs, urlparse, urlunparse

from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import (
    EventTransformer,
)
from TwitchChannelPointsMiner.classes.events.handlers.Factory import EventHandlerFactory
from TwitchChannelPointsMiner.classes.events.handlers.hooks.Hook import (
    WebhookHandler,
)
from TwitchChannelPointsMiner.utils import AttemptStrategy

__invalid_urls = {
    "https://discord.com/api/webhooks/0123456789/0a1B2c3D4e5F6g7H8i9J",
    "https://discord.com/api/webhooks/9876543210/78ad737ba0e951cdfbde",
}


class DiscordTransformer(EventTransformer[dict]):
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


def add_wait_to_url(url: str):
    """
    Adds a "wait=true" query param to the given url. This helps us to ensure message delivery.
    :param url: The url to modify
    :return: The modified url.
    """
    # Check if "wait" is already part of the url query
    scheme, netloc, path, params, query, fragment = urlparse(url)
    if "wait" not in parse_qs(query):
        query = f"{query}{('&' if query != '' else '')}wait=true"
        return urlunparse((scheme, netloc, path, params, query, fragment))
    return url


def discord(
    webhook_api_url: str,
    name: str = "Discord",
    events: list[Events] | Events | None = None,
    username: str | None = "Twitch Channel Points Miner",
    avatar_url: str | None = "https://i.imgur.com/X9fEkhT.png",
    transformer: EventTransformer[dict] | None = None,
    get_content: EventTransformer[str] | None = None,
    attempt_strategy: AttemptStrategy | None = None,
    timeout: float | tuple[float, float] | None = None,
) -> EventHandlerFactory:
    """
    Convenience function to create a webhook handler that can integrate with Discord's Incoming Webhook API.
    """
    if webhook_api_url in __invalid_urls:
        raise ValueError(
            f"URL ({webhook_api_url}) is from the example config, please use your own"
        )

    webhook_api_url = add_wait_to_url(webhook_api_url)

    return lambda default_transformer: WebhookHandler(
        name=name,
        webhook_api_url=webhook_api_url,
        events=events,
        transformer=(
            transformer
            if transformer is not None
            else DiscordTransformer(
                username=username,
                avatar_url=avatar_url,
                get_content=(
                    get_content if get_content is not None else default_transformer
                ),
            )
        ),
        attempt_strategy=attempt_strategy,
        timeout=timeout,
    )
