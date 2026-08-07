from TwitchChannelPointsMiner.classes.websocket.data.Predictions import User as WSUser
from TwitchChannelPointsMiner.utils.Utils import simple_repr


class User:
    """A User in a Prediction Event"""

    def __init__(self, _id: str, display_name: str | None):
        self.id = _id
        """The channel id of the user"""
        self.display_name = display_name
        """The display name of the user"""

    @classmethod
    def from_ws(cls, user: WSUser):
        return cls(
            _id=user.id,
            display_name=user.display_name,
        )

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, User):
            return False
        return self.id == value.id and self.display_name == value.display_name

    def __repr__(self) -> str:
        return simple_repr(self)
