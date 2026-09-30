import requests

from TwitchChannelPointsMiner.classes.EventHook import LogAttributeValidatingEventHook
from TwitchChannelPointsMiner.classes.Settings import Events


class Webhook(LogAttributeValidatingEventHook):
    def __init__(self, endpoint: str, method: str, events: list[Events] | Events):
        super().__init__(events, "skip_webhook")
        self.endpoint = endpoint
        self.method = method

    def send(self, message: str, event: Events) -> None:
        if event in self.events:
            url = self.endpoint + f"?event_name={str(event)}&message={message}"

            if self.method.lower() == "get":
                requests.get(url=url)
            elif self.method.lower() == "post":
                requests.post(url=url)
            else:
                raise ValueError("Invalid method, use POST or GET")

    def validate_record(self, record):
        return super().validate_record(record) and self.endpoint != "https://example.com/webhook"
