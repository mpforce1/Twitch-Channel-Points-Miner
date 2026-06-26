from TwitchChannelPointsMiner.classes.entities.GiftSub import GiftSub
from TwitchChannelPointsMiner.classes.gql.data.response.Pagination import Paginated
from TwitchChannelPointsMiner.utils.Utils import simple_repr


class SubscriptionBenefitResponse:
    def __init__(self, pages: Paginated[GiftSub]):
        self.pages = pages

    def __repr__(self):
        return simple_repr(self)
