from TwitchChannelPointsMiner.classes.gql.data.response.Pagination import Paginated


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


class Videos:
    def __init__(self, videos: Paginated[VideoEdge]):
        self.videos = videos
