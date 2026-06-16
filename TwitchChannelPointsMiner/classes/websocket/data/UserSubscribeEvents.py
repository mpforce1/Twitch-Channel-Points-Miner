from TwitchChannelPointsMiner.utils.Utils import simple_repr


class UserSubscribed:
    def __init__(self, channel_id: str):
        self.channel_id = channel_id

    def __repr__(self):
        return simple_repr(self)
