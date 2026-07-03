from TwitchChannelPointsMiner.classes.gql.data.response.FilterableVideoTower import (
    VideoEdge,
)
from TwitchChannelPointsMiner.classes.gql.data.response.PlaybackAccessToken import (
    VideoPlaybackAccessToken,
)
from TwitchChannelPointsMiner.utils.Utils import simple_repr


class Video:
    def __init__(
        self,
        edge: VideoEdge,
        token: VideoPlaybackAccessToken | None = None,
        viewable: bool = False,
    ):
        self.edge = edge
        self.token = token
        self.viewable = viewable

    def __repr__(self):
        return simple_repr(self)
