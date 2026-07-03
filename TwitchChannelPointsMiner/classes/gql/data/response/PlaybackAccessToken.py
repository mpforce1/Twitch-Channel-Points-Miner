from TwitchChannelPointsMiner.utils.Utils import simple_repr


class Authorization:
    def __init__(self, is_forbidden: bool, forbidden_reason_code: str):
        self.is_forbidden = is_forbidden
        self.forbidden_reason_code = forbidden_reason_code

    def __repr__(self):
        return f"Authorization({self.__dict__})"


class PlaybackAccessTokenResponse:
    def __init__(self, value: str, signature: str, authorization: Authorization):
        self.value = value
        self.signature = signature
        self.authorization = authorization

    def __repr__(self):
        return f"PlaybackAccessToken({self.__dict__})"


class VideoPlaybackAccessToken:
    def __init__(self, value: str, signature: str):
        self.value = value
        self.signature = signature

    def __repr__(self):
        return simple_repr(self)
