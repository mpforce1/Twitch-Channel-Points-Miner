from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.websocket.Pool import (
    WebSocketPoolFactory,
    WebSocketPool,
)
from TwitchChannelPointsMiner.classes.websocket.hermes.Pool import HermesWebSocketPool
from TwitchChannelPointsMiner.classes.websocket.pubsub.Pool import PubSubWebSocketPool
from TwitchChannelPointsMiner.classes.websocket.hermes import data as hermes_data
from TwitchChannelPointsMiner.constants import CLIENT_ID_WEB, HERMES_WEBSOCKET


class DefaultWebSocketPoolFactory(WebSocketPoolFactory):
    def create(self, twitch: Twitch, use_hermes: bool) -> WebSocketPool:
        if use_hermes:
            return HermesWebSocketPool(
                url=f"{HERMES_WEBSOCKET}?clientId={CLIENT_ID_WEB}",
                twitch=twitch,
                request_encoder=hermes_data.JsonEncoder(),
                response_decoder=hermes_data.JsonDecoder(),
                listeners=[],
            )
        else:
            return PubSubWebSocketPool(twitch=twitch, listeners=[])
