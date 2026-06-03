import datetime
import json

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.gql.data.response.PlaybackAccessToken import (
    PlaybackAccessTokenResponse as GQLPlaybackAccessToken,
)


class PlaybackAccessToken:
    """Twitch Playback Access Token which can be used to request stream media."""

    class Value:
        """Decoded token payload."""

        def __init__(self, expires: datetime.datetime):
            self.expires = expires
            """The expiry datetime of the token."""

    def __init__(self, raw_value: str, signature: str, value: Value):
        self.raw_value = raw_value
        """The raw token value. This can be used as is to request stream media."""
        self.signature = signature
        """The token's signature."""
        self.value = value
        """The decoded token value."""

    def __repr__(self) -> str:
        if Settings.logger.less:
            return f"PlaybackAccessToken(signature={self.signature}, expires={self.value.expires})"
        else:
            return f"PlaybackAccessToken(signature={self.signature}, expires={self.value.expires}, raw_value={self.raw_value})"

    @staticmethod
    def from_gql(token: GQLPlaybackAccessToken):
        """
        Decodes a PlaybackAccessToken from the equivalent GQL object.

        :param token: The GQL token.
        :return: The decoded token.
        :raises ValueError: If the token cannot be decoded.
        """
        decoded_value = json.loads(token.value)
        if "expires" not in decoded_value:
            raise ValueError("PlaybackAccessToken value did not contain 'expires'")
        expires = decoded_value["expires"]
        if not isinstance(expires, int):
            raise ValueError(
                f"PlaybackAccessToken's value's 'expires' was not an int (was {type(expires).__name__})"
            )
        value = PlaybackAccessToken.Value(
            expires=datetime.datetime.fromtimestamp(expires, tz=datetime.UTC)
        )
        return PlaybackAccessToken(
            raw_value=token.value, signature=token.signature, value=value
        )
