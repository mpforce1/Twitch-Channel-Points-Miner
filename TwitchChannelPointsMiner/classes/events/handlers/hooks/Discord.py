from threading import Thread
from urllib.parse import parse_qs, urlparse, urlunparse

from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import (
    EventTransformer,
)
from TwitchChannelPointsMiner.classes.events.handlers.Factory import EventHandlerFactory
from TwitchChannelPointsMiner.classes.events.handlers.hooks.Hook import (
    WebhookHandler,
)
from TwitchChannelPointsMiner.classes.events.transformers.hooks.Discord import (
    DiscordEitherTransformer,
    DiscordEmbedTransformer,
    DiscordContentTransformer,
)
from TwitchChannelPointsMiner.logger import LoggerSettings
from TwitchChannelPointsMiner.utils import AttemptStrategy

__invalid_urls = {
    "https://discord.com/api/webhooks/0123456789/0a1B2c3D4e5F6g7H8i9J",
    "https://discord.com/api/webhooks/9876543210/78ad737ba0e951cdfbde",
}


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
    use_embeds: bool = True,
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

    def factory(
        logger_settings: LoggerSettings,
        background_tasks: list[Thread],
        default_transformer: EventTransformer[str],
        account_name: str,
    ):
        nonlocal transformer
        # If the transformer is set, assume they're providing everything
        if transformer is None:
            transformer = DiscordContentTransformer(
                username=username,
                avatar_url=avatar_url,
                get_content=(
                    get_content if get_content is not None else default_transformer
                ),
            )
            if use_embeds:
                transformer = DiscordEitherTransformer(
                    base=transformer,
                    embed=DiscordEmbedTransformer(
                        translator=logger_settings.translator,
                        account_name=account_name,
                        username=username,
                        avatar_url=avatar_url,
                    ),
                )

        handler = WebhookHandler(
            name=name,
            webhook_api_url=webhook_api_url,
            events=events,
            use_json=True,
            transformer=transformer,
            attempt_strategy=attempt_strategy,
            timeout=timeout,
        )
        background_tasks.append(handler.runner)
        return handler

    return factory
