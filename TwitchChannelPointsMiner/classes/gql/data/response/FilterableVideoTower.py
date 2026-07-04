from TwitchChannelPointsMiner.classes.gql.data.response.Pagination import Paginated
from TwitchChannelPointsMiner.utils.Utils import simple_repr


class VideoEdge:
    def __init__(
        self,
        _id: str,
        broadcast_id: str,
        length_seconds: int,
    ):
        self.id = _id
        self.broadcast_id = broadcast_id
        self.length_seconds = length_seconds

    def __repr__(self):
        return simple_repr(self)


class Videos:
    def __init__(self, videos: Paginated[VideoEdge]):
        self.videos = videos
