class Error:
    def __init__(
        self, recoverable: bool, message: str, path: list[str | int] | None = None
    ):
        self.recoverable = recoverable
        self.message = message
        self.path = path

    def __repr__(self):
        return f"Error({self.__dict__})"

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Error):
            return False
        return (
            value.recoverable == self.recoverable
            and value.message == self.message
            and value.path == self.path
        )

    def __hash__(self) -> int:
        return hash((self.recoverable, self.message, hash(tuple(self.path or []))))
