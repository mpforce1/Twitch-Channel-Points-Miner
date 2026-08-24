from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.classes.events.handlers.Factory import EventHandlerFactory
from TwitchChannelPointsMiner.classes.events.handlers.hooks.Hook import (
    WebhookHandler,
)
from TwitchChannelPointsMiner.utils import AttemptStrategy


class TelegramTransformer(EventTransformer[dict]):

    def __init__(
        self,
        get_text: EventTransformer[str],
        chat_id: int,
        token: str,
        disable_notification: bool = False,
    ):
        self.chat_id = chat_id
        self.token = token
        self.disable_notification = disable_notification
        self.get_text = get_text

    def transform(self, event: Event) -> dict:
        return {
            "chat_id": self.chat_id,
            "text": self.get_text.transform(event),
            "disable_web_page_preview": True,
            "disable_notification": self.disable_notification,
        }


def telegram(
    chat_id: int,
    token: str,
    disable_notification: bool = False,
    name: str = "Telegram",
    events: list[Events] | Events | None = None,
    transformer: EventTransformer[dict] | None = None,
    get_text: EventTransformer[str] | None = None,
    attempt_strategy: AttemptStrategy | None = None,
    timeout: float | tuple[float, float] | None = None,
) -> EventHandlerFactory:
    if chat_id == 123456789:
        raise ValueError(
            f"chat_id ({chat_id}) is from the example, please use your own"
        )
    if token == "123456789:shfuihreuifheuifhiu34578347":
        raise ValueError(f"token ({token}) is from the example, please use your own")
    webhook_api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def factory(logger_settings, background_tasks, default_transformer, account_name):
        handler = WebhookHandler(
            name=name,
            webhook_api_url=webhook_api_url,
            events=events,
            transformer=(
                transformer
                if transformer is not None
                else TelegramTransformer(
                    chat_id=chat_id,
                    token=token,
                    disable_notification=disable_notification,
                    get_text=get_text if get_text is not None else default_transformer,
                )
            ),
            attempt_strategy=attempt_strategy,
            timeout=timeout,
        )
        background_tasks.append(handler.runner)
        return handler

    return factory
