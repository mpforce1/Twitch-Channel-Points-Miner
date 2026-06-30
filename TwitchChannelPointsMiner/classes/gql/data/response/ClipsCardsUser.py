from TwitchChannelPointsMiner.classes.gql.data.response.Pagination import Paginated
from TwitchChannelPointsMiner.utils import simple_repr


class Clip:
    def __init__(self, _id: str, slug: str, url: str, title: str, duration_seconds: int):
        self.id = _id
        self.slug = slug
        self.url = url
        self.title = title
        self.duration_seconds = duration_seconds

    def __repr__(self):
        return simple_repr(self)

class Response:
    def __init__(self, clips: Paginated[Clip]):
        self.clips = clips

    def __repr__(self):
        return simple_repr(self)