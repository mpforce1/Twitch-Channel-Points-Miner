from textwrap import dedent

import requests

from TwitchChannelPointsMiner.classes.EventHook import LogAttributeValidatingEventHook
from TwitchChannelPointsMiner.classes.Settings import Events


class Gotify(LogAttributeValidatingEventHook):

    def __init__(self, endpoint: str, priority: int, events: list[Events] | Events):
        super().__init__(events, "skip_gotify")
        self.endpoint = endpoint
        self.priority = priority

    def send(self, message: str, event: Events) -> None:
        if event in self.events:
            requests.post(
                url=self.endpoint,
                data={
                    "message": dedent(message),
                    "priority": self.priority
                },
            )

    def validate_record(self, record):
        return super().validate_record(record) and self.endpoint != "https://example.com/message?token=TOKEN"
