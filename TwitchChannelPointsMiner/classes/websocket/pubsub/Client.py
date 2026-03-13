import json
import logging
import time

from websocket import WebSocketApp, WebSocketConnectionClosedException

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.utils import create_nonce

logger = logging.getLogger(__name__)


class PubSubWebSocket(WebSocketApp):
    def __init__(self, index, parent_pool, *args, **kw):
        super().__init__(*args, **kw)
        self.index = index

        self.parent_pool = parent_pool
        self.is_closed = False
        self.is_opened = False

        self.is_reconnecting = False
        self.forced_close = False

        # Custom attribute
        self.topics = []
        self.pending_topics = []

        self.twitch = parent_pool.twitch

        self.last_message_timestamp = None
        self.last_message_type_channel = None

        self.last_pong = time.time()
        self.last_ping = time.time()

    # def close(self):
    #     self.forced_close = True
    #     super().close()

    def listen(self, topic, auth_token=None):
        data = {"topics": [str(topic)]}
        if topic.is_user_topic() and auth_token is not None:
            data["auth_token"] = auth_token
        nonce = create_nonce()
        self.send({"type": "LISTEN", "nonce": nonce, "data": data})

    def ping(self):
        self.send({"type": "PING"})
        self.last_ping = time.time()

    @staticmethod
    def _redact_request(request: dict):
        """
        Redacts the auth token and channel id from the given request in place if they exist.

        :param request: The request to redact.
        """
        if "data" in request:
            data = request["data"]
            if "auth_token" in data:
                data["auth_token"] = "REDACTED"
            if "topics" in data:
                data["topics"] = Settings.logger.anonymiser.topic(data["topics"])

    @staticmethod
    def _format_request(request: dict):
        """
        Formats the given request into a JSON string.

        :param request: The request to format.
        :return: The formatted request.
        """
        return json.dumps(request, separators=(",", ":"))

    def send(self, request: dict):
        try:
            request_str = self._format_request(request)
            if Settings.logger.redact_secrets:
                self._redact_request(request)
                request_str = self._format_request(request)
            logger.debug(f"#{self.index} - Send: {request_str}")
            super().send(request_str)
        except WebSocketConnectionClosedException:
            self.is_closed = True

    def elapsed_last_pong(self):
        return (time.time() - self.last_pong) // 60

    def elapsed_last_ping(self):
        return (time.time() - self.last_ping) // 60
